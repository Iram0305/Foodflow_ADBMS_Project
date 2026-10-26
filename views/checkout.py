import time

import streamlit as st

from core import hood
from core import nav
from core import orders
from core import shop
from core import shopstyle
from core import style

BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank", "Bank of Baroda"]
WALLETS = ["Paytm Wallet", "PhonePe Wallet", "Amazon Pay", "Mobikwik"]


def payment_form(method_label):
    details = {}
    if method_label == "UPI":
        details["upi"] = st.text_input("UPI ID", placeholder="yourname@okbank", key="pay_upi")
    elif method_label == "Credit / Debit card":
        details["card"] = st.text_input("Card number", placeholder="4111 1111 1111 1111", max_chars=19, key="pay_card")
        columns = st.columns(2)
        details["expiry"] = columns[0].text_input("Expiry (MM/YY)", placeholder="08/29", max_chars=5, key="pay_expiry")
        details["cvv"] = columns[1].text_input("CVV", placeholder="123", max_chars=3, type="password", key="pay_cvv")
    elif method_label == "Wallet":
        details["wallet"] = st.selectbox("Choose wallet", WALLETS, key="pay_wallet")
    elif method_label == "Net banking":
        details["bank"] = st.selectbox("Choose your bank", BANKS, key="pay_bank")
    else:
        st.info("Please keep the exact amount ready. You pay the delivery partner when the order arrives.")
    return details


def failure_message(result):
    reason = result["reason"]
    if reason.startswith("Not enough stock"):
        return "Sorry, " + reason.replace("Not enough stock for ", "") + " just ran out. Your payment was not taken. Please update your cart."
    if "declined" in reason.lower():
        return "Your bank declined the payment. You have not been charged and the items were put back in stock."
    return "We could not place your order: " + reason


def show():
    customer = st.session_state["customer"]
    cart = st.session_state["cart"]
    items = cart["items"]

    head, button = st.columns([14, 1.4])
    head.markdown("## Checkout")
    with button:
        st.write("")
        want_sql = st.button("</> SQL", key="hoodcheckout", help="See the database work behind this page")

    if not items:
        st.markdown("🛒 Your cart is empty.")
        if st.button("Browse restaurants", type="primary"):
            nav.go("discover")
        if want_sql:
            hood.checkout(st.session_state.get("last_result"))
        return

    lines = shop.cart_lines(list(items.keys()))
    subtotal = 0
    for line in lines:
        line["quantity"] = items[int(line["item_id"])]
        subtotal = subtotal + float(line["price"]) * line["quantity"]
    totals = shop.bill(subtotal)
    restaurant = shop.restaurant_info(cart["restaurant_id"], customer["latitude"], customer["longitude"])

    left, right = st.columns([3, 2], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("**Delivering to**")
            st.markdown(style.safe(customer["name"]) + " · " + style.safe(customer["phone"]) + "<br>" + style.safe(customer["address"]), unsafe_allow_html=True)
            st.caption("Estimated delivery in about " + str(restaurant["eta_minutes"]) + " minutes")
            if st.button("Change address", key="change_address"):
                nav.go("account")
        with st.container(border=True):
            st.markdown("**Payment**")
            method_label = st.radio("Payment method", list(shop.PAYMENT_METHODS.keys()), horizontal=True, label_visibility="collapsed", key="pay_method")
            details = payment_form(method_label)
            with st.expander("Payment test options"):
                st.caption("This is a simulated gateway, no real money moves. To see a failed payment and the database rollback use card 4000 0000 0000 0002, a UPI id ending in @fail, or tick the box below.")
                details["force_fail"] = st.checkbox("Force the bank to decline this payment", key="pay_force_fail")
    with right:
        with st.container(border=True):
            st.markdown("**" + style.safe(restaurant["name"]) + "**")
            st.markdown(shopstyle.bill_html(lines, totals), unsafe_allow_html=True)
            method = shop.PAYMENT_METHODS[method_label]
            label = "Pay " + shop.rupees(totals["total"])
            if method == "CASH":
                label = "Place order · pay " + shop.rupees(totals["total"]) + " on delivery"
            pay = st.button(label, type="primary", width="stretch", key="pay_now")

    if pay:
        verdict, message = shop.check_payment(method, details)
        if verdict == "invalid":
            st.error(message)
        else:
            box = st.status("Processing your payment", expanded=True)
            box.write("Securing your order and checking stock")
            time.sleep(0.5)
            if method != "CASH":
                box.write("Contacting your bank")
                time.sleep(0.6)
            mode = orders.FAILURE_MODES[0]
            if verdict == "declined":
                mode = orders.FAILURE_MODES[1]
            result = orders.place_order(customer["customer_id"], cart["restaurant_id"], dict(items), method, mode)
            st.session_state["last_result"] = result
            if result["outcome"] == "COMMITTED":
                box.update(label="Payment successful", state="complete")
                st.session_state["track_order_id"] = int(result["order_id"])
                cart["items"] = {}
                time.sleep(0.8)
                nav.go("track")
            else:
                box.update(label="Payment failed", state="error")
                st.error(failure_message(result))
                st.caption("Open </> SQL at the top right to see the transaction that was rolled back.")

    if want_sql:
        hood.checkout(st.session_state.get("last_result"))
    style.footer()

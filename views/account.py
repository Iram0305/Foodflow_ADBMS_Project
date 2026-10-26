import streamlit as st

from core import hood
from core import shop
from core import style


def sign_out():
    for key in ["customer", "cart", "restaurant_id", "track_order_id", "last_result", "celebrated", "track_done"]:
        st.session_state.pop(key, None)


def show():
    customer = st.session_state["customer"]
    head, button = st.columns([14, 1.4])
    head.markdown("## Your account")
    with button:
        st.write("")
        want_sql = st.button("</> SQL", key="hoodaccount", help="See the database work behind this page")
    left, right = st.columns([2, 3], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="sf-avatar" style="width:72px;height:72px;font-size:38px">🙂</div>', unsafe_allow_html=True)
            st.markdown("### " + style.safe(customer["name"]))
            st.markdown("📞 " + style.safe(customer["phone"]) + "<br>✉️ " + style.safe(customer["email"]) + "<br>Customer #" + str(customer["customer_id"]) +
                        " · member since " + customer["joined_on"].strftime("%b %Y"), unsafe_allow_html=True)
            st.button("Sign out", on_click=sign_out, width="stretch", key="signout")
    with right:
        with st.container(border=True):
            st.markdown("**Delivery address**")
            names = shop.locality_names()
            current = customer["locality"] if customer["locality"] in names else names[0]
            with st.form("address"):
                locality = st.selectbox("Area", names, index=names.index(current))
                address = st.text_input("Flat, building and street", value=customer["address"])
                save = st.form_submit_button("Save address", type="primary")
            if save:
                moved = locality != customer["locality"]
                ok, message, sql_text = shop.update_address(customer["customer_id"], address, locality, not moved)
                st.session_state["account_sql"] = sql_text
                if ok:
                    st.session_state["customer"] = shop.get_customer(customer["customer_id"])
                    st.toast("Address updated")
                    st.rerun()
                else:
                    st.error(message)
    if want_sql:
        hood.account(customer["customer_id"], st.session_state.get("account_sql", ""))
    style.footer()

import pandas as pd
import streamlit as st

from core import database
from core import orders
from core import style


def show():
    style.hero("Rubric 3A · Transaction management",
               "Place an order, watch ACID happen",
               "Checking stock, reducing inventory, creating the order, its items, its history and the payment all happen inside one transaction. "
               "If anything fails, PostgreSQL rolls the whole thing back as if it never started.",
               ["Atomicity", "Consistency", "Isolation", "Durability", "SELECT ... FOR UPDATE", "ROLLBACK"])

    customers = database.fetch("SELECT customer_id, name, locality FROM customer ORDER BY name")
    restaurants = database.fetch("SELECT restaurant_id, name, cuisine, locality, rating FROM restaurant ORDER BY name")

    style.section("01", "Build the order")
    left, right = st.columns(2)
    customer_labels = {}
    for row in customers.to_dict("records"):
        customer_labels[row["name"] + " · " + row["locality"] + " (#" + str(row["customer_id"]) + ")"] = row["customer_id"]
    restaurant_labels = {}
    for row in restaurants.to_dict("records"):
        restaurant_labels[row["name"] + " · " + row["cuisine"] + " · " + row["locality"]] = row["restaurant_id"]

    customer_pick = left.selectbox("Customer", list(customer_labels.keys()), index=100)
    restaurant_pick = right.selectbox("Restaurant", list(restaurant_labels.keys()), index=10)
    customer_id = customer_labels[customer_pick]
    restaurant_id = restaurant_labels[restaurant_pick]

    menu = database.fetch("SELECT item_id, item_name, category, price, stock FROM menu_item WHERE restaurant_id = %s ORDER BY category, item_name", (int(restaurant_id),))
    menu["quantity"] = 0
    if len(menu) > 0:
        menu.loc[0, "quantity"] = 1
    edited = st.data_editor(menu, hide_index=True, width="stretch", key="menu_editor_" + str(restaurant_id),
                            disabled=["item_id", "item_name", "category", "price", "stock"],
                            column_config={"quantity": st.column_config.NumberColumn("Quantity", min_value=0, max_value=500, step=1),
                                           "price": st.column_config.NumberColumn("Price (Rs)", format="%.0f"),
                                           "stock": st.column_config.ProgressColumn("Stock left", min_value=0, max_value=160, format="%d")})

    cart = {}
    subtotal = 0
    for row in edited.to_dict("records"):
        if row["quantity"] and int(row["quantity"]) > 0:
            cart[int(row["item_id"])] = int(row["quantity"])
            subtotal = subtotal + float(row["price"]) * int(row["quantity"])

    left, middle, right = st.columns([1, 1, 2])
    method = left.selectbox("Payment method", ["UPI", "CARD", "WALLET", "NETBANKING", "CASH"])
    middle.metric("Cart subtotal", style.money(subtotal), str(len(cart)) + " item(s)")
    failure = right.radio("Inject a failure to test atomicity", orders.FAILURE_MODES, index=0)
    st.caption("Tip: type a quantity larger than the stock to see the stock check fail and roll back.")

    if st.button("Place order in one transaction", type="primary", disabled=len(cart) == 0):
        with st.spinner("Running transaction..."):
            result = orders.place_order(customer_id, restaurant_id, cart, method, failure)
        st.session_state["last_order_result"] = result

    result = st.session_state.get("last_order_result")
    if result is None:
        style.section("02", "Transaction log", "Place an order to see every SQL statement the transaction runs.")
        style.footer()
        return

    style.section("02", "Transaction log", "Every statement sent to PostgreSQL, in order, with timing.")
    if result["outcome"] == "COMMITTED":
        style.banner("good", "✅", "COMMITTED · Order #" + str(result["order_id"]) + " is confirmed",
                     "All changes were made permanent together. The order is now in PostgreSQL and its tracking document is in MongoDB.")
    else:
        text = "Reason: " + result["reason"] + ". "
        if result["order_id"] is not None:
            text = text + "Order #" + str(result["order_id"]) + " was created inside the transaction, but it "
            if result["order_exists"]:
                text = text + "still exists (unexpected!)."
            else:
                text = text + "no longer exists. Stock is back to where it was."
        style.banner("bad", "↩️", "ROLLED BACK · nothing was saved", text)

    left, right = st.columns([3, 2])
    with left:
        style.steps(result["steps"])
    with right:
        st.markdown("**Stock before vs after**")
        rows = []
        for item_id in result["before"]:
            rows.append({"item_id": item_id, "before": result["before"][item_id], "after": result["after"].get(item_id),
                         "changed": result["before"][item_id] != result["after"].get(item_id)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if result["order_id"] is not None:
            st.markdown("**Verify in the database**")
            check_sql = "SELECT order_id, status, total_amount FROM orders WHERE order_id = " + str(result["order_id"]) + ";"
            st.code(check_sql, language="sql")
            st.dataframe(database.fetch(check_sql), hide_index=True, width="stretch")
            if result["outcome"] == "COMMITTED":
                st.info("Open **Live Tracking** to move order #" + str(result["order_id"]) + " through its lifecycle.")
        style.card("What to say in the viva",
                   "Atomicity: all steps succeed or none do. Consistency: CHECK and FK constraints are never broken. "
                   "Isolation: FOR UPDATE stops another order from reading the same stock mid-way. Durability: after COMMIT the WAL makes it survive a crash.")
    style.footer()

import streamlit as st

from core import database
from core import hood
from core import shop
from core import style


def start_session(customer_id):
    customer = shop.get_customer(customer_id)
    st.session_state["customer"] = customer
    st.session_state["cart"] = {"restaurant_id": None, "items": {}}
    st.session_state["speed"] = "Demo (about 2 min)"
    st.rerun()


def show():
    left, right = st.columns([5, 4], gap="large")
    with left:
        st.markdown('<div class="sf-welcome"><div style="position:relative"><div class="ff-kicker">FoodFlow · Mumbai</div>'
                    "<h1>Hungry? We bring Mumbai's best kitchens to your door.</h1>"
                    "<p>120 restaurants, 12 cuisines and riders tracked live on the map. Sign in to order.</p>"
                    '<div class="sf-emoji-row">🍛 🍕 🥡 🍔 🍰</div></div></div>', unsafe_allow_html=True)
    with right:
        top, button = st.columns([5, 1.6])
        top.markdown("### Welcome")
        with button:
            st.write("")
            if st.button("</> SQL", key="hoodlogin", help="See the database work behind this page"):
                hood.login(st.session_state.get("signup_sql", ""))
        tabs = st.tabs(["I already have an account", "Create my account"])
        with tabs[0]:
            labels = shop.customer_options()
            st.caption(style.number(len(labels)) + " customers are already registered. Pick yours, or any of them, to continue.")
            pick = st.selectbox("Find your account", list(labels.keys()), index=None, placeholder="Type your name or phone number")
            if st.button("Continue", type="primary", width="stretch", disabled=pick is None, key="continue_existing"):
                start_session(labels[pick])
        with tabs[1]:
            with st.form("signup"):
                name = st.text_input("Full name", placeholder="Iram Shaikh")
                columns = st.columns(2)
                phone = columns[0].text_input("Mobile number", placeholder="98xxxxxxxx", max_chars=10)
                email = columns[1].text_input("Email", placeholder="you@example.com")
                locality = st.selectbox("Your area in Mumbai", shop.locality_names(), index=shop.locality_names().index("Kanjurmarg"))
                address = st.text_input("Flat, building and street", placeholder="Flat 302, NG Royal Park, LBS Marg")
                submitted = st.form_submit_button("Create account and continue", type="primary", width="stretch")
            if submitted:
                ok, result, sql_text = shop.create_customer(name, phone, email, address, locality)
                st.session_state["signup_sql"] = sql_text
                if ok:
                    st.toast("Welcome to FoodFlow, " + name.strip().split(" ")[0] + "!")
                    start_session(result)
                else:
                    st.error(result)
    st.write("")
    style.footer()

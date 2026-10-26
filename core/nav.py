import streamlit as st

pages = {}


def go(name):
    st.switch_page(pages[name])

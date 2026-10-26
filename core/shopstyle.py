import streamlit as st

from core import style
from core.shop import rupees

CUISINE_LOOK = {
    "North Indian": ("🍛", "#FDE3C6", "#F7B267"),
    "South Indian": ("🥞", "#FCEFC7", "#F2C14E"),
    "Chinese": ("🥡", "#FBD9D3", "#F28B82"),
    "Italian": ("🍕", "#FFE0D1", "#F4845F"),
    "Biryani": ("🍗", "#F8E1C4", "#D9A05B"),
    "Street Food": ("🥙", "#FFE7B8", "#F5B83D"),
    "Cafe": ("☕", "#EBDDCF", "#B08968"),
    "Desserts": ("🍰", "#FBD8E6", "#F08CB0"),
    "Coastal": ("🦐", "#D5EDF0", "#6BB6C2"),
    "Burgers": ("🍔", "#FFDFC2", "#F29E4C"),
    "Healthy": ("🥗", "#DDF0D5", "#7BC47F"),
    "Mughlai": ("🍢", "#F3DCCB", "#C9835A"),
}

CSS = """
<style>
.sf-banner { position: relative; overflow: hidden; background: linear-gradient(120deg, #E8532B 0%, #F2793F 55%, #F2A541 100%); color: #fff;
             border-radius: 24px; padding: 30px 36px; margin-bottom: 18px; }
.sf-banner h1 { color: #fff !important; font-size: 2.3rem; margin: 0 0 6px 0; line-height: 1.1; }
.sf-banner p { margin: 0; opacity: 0.93; font-size: 1.02rem; }
.sf-banner .sf-float { position: absolute; right: 30px; top: 14px; font-size: 76px; letter-spacing: 8px; opacity: 0.92; }
.sf-pill { display: inline-block; background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.35); padding: 4px 12px; border-radius: 999px;
           font-size: 12.5px; font-weight: 600; margin-top: 14px; margin-right: 8px; }

.sf-tile { border-radius: 14px; height: 92px; display: flex; align-items: center; justify-content: space-between; padding: 0 18px; margin-bottom: 10px; }
.sf-tile-emoji { font-size: 50px; }
.sf-tile-tag { background: rgba(255,255,255,0.8); color: #1E1B18; border-radius: 999px; padding: 3px 10px; font-size: 11.5px; font-weight: 700; }
.sf-name { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.12rem; color: #1E1B18; line-height: 1.2; }
.sf-sub { color: #7A6C5D; font-size: 13px; margin-top: 2px; }
.sf-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 9px; font-size: 13px; color: #5B4E42; align-items: center; }
.sf-rating { background: #2A9D8F; color: #fff; font-weight: 700; border-radius: 8px; padding: 2px 8px; font-size: 12.5px; }
.sf-rating-mid { background: #E0A100; }
.sf-rating-low { background: #C8102E; }
.sf-badge { background: #FFF1E6; color: #B5421B; border-radius: 6px; padding: 2px 8px; font-size: 11.5px; font-weight: 700; }
.sf-badge-green { background: #E6F4F1; color: #1B7D70; }

.sf-veg, .sf-nonveg { display: inline-block; width: 15px; height: 15px; border: 2px solid #2A9D8F; border-radius: 3px; position: relative; vertical-align: -2px; margin-right: 7px; }
.sf-veg:after, .sf-nonveg:after { content: ""; position: absolute; width: 7px; height: 7px; border-radius: 50%; background: #2A9D8F; left: 2px; top: 2px; }
.sf-nonveg { border-color: #B5421B; }
.sf-nonveg:after { background: #B5421B; }

.sf-item { padding: 12px 4px 6px 4px; border-bottom: 1px dashed #E6D9C9; }
.sf-item-name { font-weight: 700; color: #1E1B18; font-size: 1.0rem; }
.sf-item-price { color: #1E1B18; font-weight: 600; margin-top: 2px; }
.sf-low { color: #C8102E; font-size: 12.5px; font-weight: 600; }
.sf-soldout { color: #8A7B6D; font-size: 12.5px; font-weight: 600; }
.sf-category { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.25rem; margin: 22px 0 2px 0; }

.sf-bill-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 14.5px; color: #5B4E42; }
.sf-bill-total { display: flex; justify-content: space-between; padding: 10px 0 2px 0; margin-top: 6px; border-top: 2px solid #1E1B18;
                 font-weight: 800; font-size: 1.15rem; color: #1E1B18; }
.sf-line { display: flex; justify-content: space-between; gap: 10px; padding: 5px 0; font-size: 14.5px; color: #1E1B18; }
.sf-line span:last-child { white-space: nowrap; }

.sf-status { background: #1E1B18; color: #FBF7F2; border-radius: 22px; padding: 24px 28px; display: flex; gap: 20px; align-items: center; margin-bottom: 14px; }
.sf-status-icon { font-size: 54px; }
.sf-status-title { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.7rem; line-height: 1.1; }
.sf-status-sub { color: #D9CFC4; margin-top: 4px; }
.sf-eta { margin-left: auto; text-align: right; }
.sf-eta-label { font-size: 11.5px; letter-spacing: 0.12em; text-transform: uppercase; color: #F2A541; font-weight: 700; }
.sf-eta-value { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.9rem; font-weight: 800; }

.sf-rider { display: flex; gap: 14px; align-items: center; }
.sf-avatar { width: 52px; height: 52px; border-radius: 50%; background: #FFF1E6; display: grid; place-items: center; font-size: 28px; }

.sf-order-title { font-weight: 800; font-size: 1.05rem; color: #1E1B18; }
.sf-chip { display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.sf-chip-DELIVERED { background: #E6F4F1; color: #1B7D70; }
.sf-chip-CANCELLED { background: #FCE8E6; color: #A3281C; }
.sf-chip-live { background: #FFF1E6; color: #B5421B; }

.sf-welcome { background: #1E1B18; color: #FBF7F2; border-radius: 26px; padding: 40px; position: relative; overflow: hidden; min-height: 360px; }
.sf-welcome h1 { color: #FBF7F2 !important; font-size: 2.7rem; line-height: 1.05; margin-bottom: 10px; }
.sf-welcome p { color: #D9CFC4; font-size: 1.05rem; }
.sf-welcome:before { content: ""; position: absolute; right: -60px; top: -100px; width: 360px; height: 360px; border-radius: 50%;
                     background: radial-gradient(circle, rgba(232,83,43,0.6) 0%, rgba(232,83,43,0) 70%); }
.sf-welcome .sf-emoji-row { font-size: 44px; letter-spacing: 10px; margin-top: 26px; position: relative; }

[class*="st-key-hood"] button { opacity: 0.6; font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 2px 8px; min-height: 28px;
                                border: 1px dashed #B9AA9A; border-radius: 8px; color: #7A6C5D; }
[class*="st-key-hood"] button:hover { opacity: 1; border-color: #E8532B; color: #E8532B; }
[class*="st-key-add"] button { border: 1.5px solid #2A9D8F; color: #1B7D70; font-weight: 800; min-height: 34px; background: #fff; }
[class*="st-key-plus"] button, [class*="st-key-minus"] button { min-height: 34px; padding: 0 6px; font-weight: 800; border: 1.5px solid #2A9D8F; color: #1B7D70; background: #fff; }
.sf-qty { text-align: center; font-weight: 800; font-size: 1.05rem; padding-top: 4px; }
</style>
"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)


def look(cuisine):
    return CUISINE_LOOK.get(cuisine, ("🍽️", "#EEE", "#CCC"))


def rating_badge(value):
    value = float(value)
    css = "sf-rating"
    if value < 3.5:
        css = "sf-rating sf-rating-low"
    elif value < 4.0:
        css = "sf-rating sf-rating-mid"
    return '<span class="' + css + '">★ ' + str(round(value, 1)) + "</span>"


def veg_dot(is_veg):
    if is_veg:
        return '<span class="sf-veg"></span>'
    return '<span class="sf-nonveg"></span>'


def page_header(title, subtitle, hood_key):
    left, right = st.columns([14, 1.4])
    with left:
        st.markdown("## " + title)
        if subtitle:
            st.caption(subtitle)
    with right:
        st.write("")
        return st.button("</> SQL", key="hood" + hood_key, help="See the database work behind this page")


def restaurant_card_html(row, badge_text=""):
    emoji, light, strong = look(row["cuisine"])
    tag = ""
    if badge_text:
        tag = '<span class="sf-tile-tag">' + badge_text + "</span>"
    veg_text = ""
    if row["is_veg"]:
        veg_text = '<span class="sf-badge sf-badge-green">Pure veg</span>'
    return ('<div class="sf-tile" style="background: linear-gradient(135deg, ' + light + ", " + strong + ');">'
            '<span class="sf-tile-emoji">' + emoji + "</span>" + tag + "</div>"
            '<div class="sf-name">' + style.safe(row["name"]) + "</div>"
            '<div class="sf-sub">' + style.safe(row["cuisine"]) + " · " + style.safe(row["locality"]) + "</div>"
            '<div class="sf-meta">' + rating_badge(row["rating"]) + "<span>" + str(row["eta_minutes"]) + " mins</span><span>" +
            str(row["distance_km"]) + " km</span><span>" + rupees(row["cost_for_two"]) + " for two</span>" + veg_text + "</div>")


def bill_html(lines, totals):
    parts = []
    for line in lines:
        parts.append('<div class="sf-line"><span>' + veg_dot(line["is_veg"]) + style.safe(line["item_name"]) + " × " + str(line["quantity"]) +
                     "</span><span>" + rupees(float(line["price"]) * line["quantity"]) + "</span></div>")
    parts.append('<div style="height:8px"></div>')
    parts.append('<div class="sf-bill-row"><span>Item total</span><span>' + rupees(totals["subtotal"]) + "</span></div>")
    fee = rupees(totals["delivery_fee"])
    if totals["delivery_fee"] == 0:
        fee = "FREE"
    parts.append('<div class="sf-bill-row"><span>Delivery fee</span><span>' + fee + "</span></div>")
    parts.append('<div class="sf-bill-row"><span>Taxes (5%)</span><span>' + rupees(totals["taxes"]) + "</span></div>")
    parts.append('<div class="sf-bill-total"><span>To pay</span><span>' + rupees(totals["total"]) + "</span></div>")
    return "".join(parts)

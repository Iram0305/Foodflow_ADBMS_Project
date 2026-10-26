import html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

COLORS = ["#E8532B", "#1E1B18", "#F2A541", "#2A9D8F", "#8E5572", "#577590", "#C9A227", "#6D9886", "#B5838D", "#3D5A80", "#EE964B", "#7A6C5D"]
ORANGE = "#E8532B"
INK = "#1E1B18"
GREEN = "#2A9D8F"
RED = "#C8102E"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, p, li, label, input, textarea, button {
    font-family: 'Plus Jakarta Sans', sans-serif;
}
h1, h2, h3, h4 { font-family: 'Bricolage Grotesque', sans-serif !important; letter-spacing: -0.02em; }
code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }

.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1280px; }

[data-testid="stSidebar"] { background: #1E1B18; }
[data-testid="stSidebar"] * { color: #F4EDE4; }
[data-testid="stSidebar"] .stButton button { background: #2B2622; border: 1px solid #3A332D; color: #F4EDE4; }
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] { border-radius: 10px; }
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover { background: #2B2622; }
[data-testid="stSidebar"] [aria-current="page"] { background: #E8532B !important; }
[data-testid="stSidebarNavSeparator"] { border-color: #3A332D; }

.ff-brand { display: flex; align-items: center; gap: 12px; padding: 4px 4px 14px 4px; }
.ff-logo { width: 42px; height: 42px; border-radius: 12px; background: #E8532B; display: grid; place-items: center;
           font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 22px; color: #fff; }
.ff-brand-name { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 22px; line-height: 1; }
.ff-brand-sub { font-size: 11px; opacity: 0.65; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 4px; }

.ff-status { background: #2B2622; border: 1px solid #3A332D; border-radius: 12px; padding: 10px 12px; margin: 6px 0; font-size: 13px; }
.ff-status b { display: block; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.6; font-weight: 600; margin-bottom: 2px; }
.ff-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }

.ff-hero { position: relative; overflow: hidden; background: #1E1B18; color: #FBF7F2; border-radius: 22px;
           padding: 34px 38px; margin-bottom: 22px; }
.ff-hero:before { content: ""; position: absolute; right: -80px; top: -120px; width: 380px; height: 380px; border-radius: 50%;
                  background: radial-gradient(circle, rgba(232,83,43,0.55) 0%, rgba(232,83,43,0) 70%); }
.ff-hero:after { content: ""; position: absolute; right: 120px; bottom: -160px; width: 300px; height: 300px; border-radius: 50%;
                 background: radial-gradient(circle, rgba(242,165,65,0.35) 0%, rgba(242,165,65,0) 70%); }
.ff-kicker { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: #F2A541; font-weight: 700; }
.ff-hero h1 { color: #FBF7F2 !important; font-size: 2.6rem; margin: 6px 0 8px 0; font-weight: 800; line-height: 1.05; }
.ff-hero p { color: #D9CFC4; font-size: 1.02rem; max-width: 760px; margin: 0; position: relative; z-index: 2; }
.ff-chips { margin-top: 16px; position: relative; z-index: 2; }
.ff-chip { display: inline-block; padding: 5px 12px; margin: 0 6px 6px 0; border-radius: 999px; font-size: 12px; font-weight: 600;
           background: rgba(251,247,242,0.08); border: 1px solid rgba(251,247,242,0.18); color: #FBF7F2; }
.ff-chip-light { background: #F3EBE1; border: 1px solid #E6D9C9; color: #5B4E42; }

.ff-kpi { background: #FFFFFF; border: 1px solid #ECE2D6; border-radius: 18px; padding: 18px 20px; height: 100%;
          box-shadow: 0 1px 0 rgba(30,27,24,0.03); }
.ff-kpi-label { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #8A7B6D; font-weight: 700; }
.ff-kpi-value { white-space: nowrap; font-family: 'Bricolage Grotesque', sans-serif; font-size: 2rem; font-weight: 800; color: #1E1B18; line-height: 1.15; margin-top: 4px; }
.ff-kpi-sub { font-size: 13px; color: #8A7B6D; margin-top: 2px; }
.ff-kpi-accent { border-top: 4px solid #E8532B; }

.ff-section { margin: 30px 0 10px 0; }
.ff-section-num { font-family: 'JetBrains Mono', monospace; color: #E8532B; font-size: 13px; font-weight: 600; }
.ff-section-title { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.55rem; font-weight: 800; color: #1E1B18; margin: 2px 0 2px 0; }
.ff-section-text { color: #6B5D50; font-size: 0.97rem; max-width: 880px; }

.ff-card { background: #FFFFFF; border: 1px solid #ECE2D6; border-radius: 18px; padding: 18px 20px; margin-bottom: 12px; }
.ff-card h4 { margin: 0 0 6px 0; font-size: 1.1rem; }
.ff-card p { color: #6B5D50; margin: 0; font-size: 0.94rem; }

.ff-step { display: grid; grid-template-columns: 26px 1fr 70px; gap: 12px; padding: 12px 4px; border-bottom: 1px dashed #E6D9C9; }
.ff-step:last-child { border-bottom: none; }
.ff-step-dot { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; color: #fff; font-size: 12px; font-weight: 700; margin-top: 2px; }
.ff-step-label { font-weight: 700; color: #1E1B18; }
.ff-step-sql { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #5B4E42; background: #FBF7F2; border: 1px solid #F0E6DA;
               border-radius: 8px; padding: 6px 9px; margin-top: 6px; white-space: pre-wrap; }
.ff-step-detail { font-size: 13px; color: #6B5D50; margin-top: 4px; }
.ff-step-ms { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #8A7B6D; text-align: right; }

.ff-banner { border-radius: 18px; padding: 18px 22px; margin: 10px 0 16px 0; display: flex; gap: 16px; align-items: center; }
.ff-banner-icon { font-size: 30px; }
.ff-banner-title { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.35rem; }
.ff-banner-text { font-size: 0.95rem; opacity: 0.9; }
.ff-good { background: #E6F4F1; border: 1px solid #BFE3DB; color: #134E45; }
.ff-bad { background: #FCE8E6; border: 1px solid #F4C2BC; color: #7A1A10; }
.ff-warn { background: #FFF4E0; border: 1px solid #F6D9A6; color: #6B4A0E; }

.ff-lanes { display: grid; grid-template-columns: 1fr 74px 1fr; gap: 0; background: #FFFFFF; border: 1px solid #ECE2D6; border-radius: 18px; overflow: hidden; }
.ff-lane-head { padding: 12px 16px; font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; background: #F3EBE1; }
.ff-lane-time { padding: 9px 6px; text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #8A7B6D; background: #FBF7F2;
                border-left: 1px solid #ECE2D6; border-right: 1px solid #ECE2D6; }
.ff-lane-cell { padding: 9px 16px; font-size: 13.5px; border-top: 1px solid #F3EBE1; min-height: 20px; }
.ff-lane-cell code { font-size: 11.5px; color: #8A7B6D; background: none; display: block; margin-top: 3px; white-space: pre-wrap; }
.ff-lane-a { border-left: 4px solid #E8532B; }
.ff-lane-b { border-left: 4px solid #2A9D8F; }

.ff-tracker { display: flex; gap: 0; margin: 10px 0 18px 0; }
.ff-track-step { flex: 1; text-align: center; position: relative; }
.ff-track-step:before { content: ""; position: absolute; top: 15px; left: -50%; width: 100%; height: 4px; background: #E6D9C9; z-index: 0; }
.ff-track-step:first-child:before { display: none; }
.ff-track-done:before { background: #E8532B; }
.ff-track-circle { width: 34px; height: 34px; border-radius: 50%; margin: 0 auto; position: relative; z-index: 1; display: grid; place-items: center;
                   background: #F3EBE1; color: #8A7B6D; font-weight: 800; border: 3px solid #FBF7F2; }
.ff-track-done .ff-track-circle { background: #E8532B; color: #fff; }
.ff-track-current .ff-track-circle { box-shadow: 0 0 0 6px rgba(232,83,43,0.2); }
.ff-track-name { font-size: 12px; font-weight: 700; margin-top: 6px; color: #1E1B18; letter-spacing: 0.04em; }
.ff-track-time { font-size: 11px; color: #8A7B6D; }

.ff-arch { display: grid; grid-template-columns: 1fr 34px 1fr 34px 2.4fr; align-items: stretch; gap: 0; margin: 8px 0 6px 0; }
.ff-arch-box { border-radius: 18px; padding: 18px; }
.ff-arch-dark { background: #1E1B18; color: #FBF7F2; display: flex; flex-direction: column; justify-content: center; }
.ff-arch-dark b { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.15rem; }
.ff-arch-light { background: #FFFFFF; border: 1px solid #ECE2D6; display: flex; flex-direction: column; justify-content: center; }
.ff-arch-light b { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.15rem; }
.ff-arch-small { font-size: 12.5px; opacity: 0.75; margin-top: 6px; line-height: 1.45; }
.ff-arch-arrow { display: grid; place-items: center; color: #E8532B; font-size: 22px; font-weight: 800; }
.ff-arch-stores { display: flex; flex-direction: column; gap: 12px; }
.ff-arch-store { border-radius: 18px; padding: 14px 16px; background: #FFFFFF; }
.ff-arch-pg { border: 2px solid #E8532B; }
.ff-arch-mg { border: 2px solid #2A9D8F; }
.ff-arch-title { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.05rem; margin-bottom: 8px; }
.ff-arch-tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.ff-arch-tile { background: #FBF7F2; border: 1px solid #F0E6DA; border-radius: 10px; padding: 8px 10px; font-size: 12.5px; }
.ff-arch-tile b { display: block; font-size: 13px; }
.ff-rubric { display: grid; grid-template-columns: 70px 1.3fr 1.3fr 3fr; gap: 0; background: #FFFFFF; border: 1px solid #ECE2D6; border-radius: 18px; overflow: hidden; }
.ff-rubric div { padding: 11px 14px; border-top: 1px solid #F3EBE1; font-size: 14px; }
.ff-rubric .ff-rh { background: #1E1B18; color: #FBF7F2; font-weight: 700; border-top: none; font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; }
.ff-rubric .ff-rm { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.2rem; color: #E8532B; }
.ff-foot { margin-top: 40px; padding-top: 16px; border-top: 1px solid #ECE2D6; color: #8A7B6D; font-size: 13px; }

div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #ECE2D6; border-radius: 16px; padding: 12px 16px; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { background: #F3EBE1; border-radius: 10px 10px 0 0; padding: 8px 16px; font-weight: 600; }
.stTabs [aria-selected="true"] { background: #1E1B18 !important; color: #FBF7F2 !important; }
.stButton button[kind="primary"] { border-radius: 12px; font-weight: 700; padding: 0.55rem 1.2rem; }
.stButton button { border-radius: 12px; font-weight: 600; }
[data-testid="stDataFrame"] { border: 1px solid #ECE2D6; border-radius: 14px; overflow: hidden; }
</style>
"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)
    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(family="Plus Jakarta Sans, sans-serif", color=INK, size=13),
        colorway=COLORS,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor="#EFE6DB", zerolinecolor="#EFE6DB"),
        yaxis=dict(gridcolor="#EFE6DB", zerolinecolor="#EFE6DB"),
        title=dict(font=dict(family="Bricolage Grotesque, sans-serif", size=17)),
        hoverlabel=dict(bgcolor="#1E1B18", font=dict(color="#FBF7F2")),
    )
    pio.templates["foodflow"] = template
    pio.templates.default = "plotly_white+foodflow"


def safe(text):
    return html.escape(str(text))


def hero(kicker, title, text, chips=None):
    chip_html = ""
    if chips:
        chip_html = '<div class="ff-chips">'
        for chip in chips:
            chip_html = chip_html + '<span class="ff-chip">' + safe(chip) + "</span>"
        chip_html = chip_html + "</div>"
    st.markdown('<div class="ff-hero"><div class="ff-kicker">' + safe(kicker) + "</div><h1>" + safe(title) + "</h1><p>" + safe(text) + "</p>" + chip_html + "</div>",
                unsafe_allow_html=True)


def kpis(items):
    columns = st.columns(len(items))
    for i in range(len(items)):
        label, value, sub = items[i]
        accent = ""
        if i == 0:
            accent = " ff-kpi-accent"
        columns[i].markdown('<div class="ff-kpi' + accent + '"><div class="ff-kpi-label">' + safe(label) + '</div><div class="ff-kpi-value">' + safe(value) +
                            '</div><div class="ff-kpi-sub">' + safe(sub) + "</div></div>", unsafe_allow_html=True)


def section(number, title, text=""):
    st.markdown('<div class="ff-section"><div class="ff-section-num">' + safe(number) + '</div><div class="ff-section-title">' + safe(title) +
                '</div><div class="ff-section-text">' + safe(text) + "</div></div>", unsafe_allow_html=True)


def chips(items):
    chip_html = ""
    for item in items:
        chip_html = chip_html + '<span class="ff-chip ff-chip-light">' + safe(item) + "</span>"
    st.markdown(chip_html, unsafe_allow_html=True)


def card(title, text):
    st.markdown('<div class="ff-card"><h4>' + safe(title) + "</h4><p>" + safe(text) + "</p></div>", unsafe_allow_html=True)


def banner(kind, icon, title, text):
    css = {"good": "ff-good", "bad": "ff-bad", "warn": "ff-warn"}[kind]
    st.markdown('<div class="ff-banner ' + css + '"><div class="ff-banner-icon">' + icon + '</div><div><div class="ff-banner-title">' + safe(title) +
                '</div><div class="ff-banner-text">' + safe(text) + "</div></div></div>", unsafe_allow_html=True)


def steps(step_list):
    parts = ['<div class="ff-card">']
    number = 1
    for step in step_list:
        color = GREEN
        mark = str(number)
        if not step["ok"]:
            color = RED
            mark = "!"
        sql_html = ""
        if step["sql"]:
            sql_html = '<div class="ff-step-sql">' + safe(step["sql"]) + "</div>"
        detail = step["detail"]
        if isinstance(detail, list):
            if len(detail) == 0:
                detail = "0 rows returned"
            else:
                detail = "Returned: " + ", ".join(str(tuple(row)) for row in detail[:3])
        parts.append('<div class="ff-step"><div class="ff-step-dot" style="background:' + color + '">' + mark + '</div><div><div class="ff-step-label">' +
                     safe(step["label"]) + "</div>" + sql_html + '<div class="ff-step-detail">' + safe(detail) + '</div></div><div class="ff-step-ms">' +
                     str(step["ms"]) + " ms</div></div>")
        number += 1
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def lanes(events, left="Customer A", right="Customer B"):
    parts = ['<div class="ff-lanes"><div class="ff-lane-head">' + safe(left) + '</div><div class="ff-lane-head" style="text-align:center">time</div><div class="ff-lane-head">' +
             safe(right) + "</div>"]
    for event in events:
        text = "<b>" + safe(event["action"]) + "</b>"
        if event["sql"]:
            text = text + "<code>" + safe(event["sql"]) + "</code>"
        if event["customer"] == left:
            parts.append('<div class="ff-lane-cell ff-lane-a">' + text + '</div><div class="ff-lane-time">' + str(event["ms"]) + ' ms</div><div class="ff-lane-cell"></div>')
        else:
            parts.append('<div class="ff-lane-cell"></div><div class="ff-lane-time">' + str(event["ms"]) + ' ms</div><div class="ff-lane-cell ff-lane-b">' + text + "</div>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def tracker(flow, reached, times):
    parts = ['<div class="ff-tracker">']
    last_index = -1
    for i in range(len(flow)):
        if flow[i] in reached:
            last_index = i
    for i in range(len(flow)):
        css = "ff-track-step"
        if i <= last_index:
            css = css + " ff-track-done"
        if i == last_index:
            css = css + " ff-track-current"
        when = times.get(flow[i], "")
        parts.append('<div class="' + css + '"><div class="ff-track-circle">' + str(i + 1) + '</div><div class="ff-track-name">' + safe(flow[i].replace("_", " ")) +
                     '</div><div class="ff-track-time">' + safe(when) + "</div></div>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def money(value):
    value = float(value)
    if value >= 10000000:
        return "₹" + str(round(value / 10000000, 2)) + " Cr"
    if value >= 100000:
        return "₹" + str(round(value / 100000, 1)) + " L"
    return "₹" + format(round(value), ",")


def number(value):
    return format(int(value), ",")


def footer():
    st.markdown('<div class="ff-foot">FoodFlow · Hybrid ADBMS mini project · PostgreSQL + MongoDB + Streamlit</div>', unsafe_allow_html=True)

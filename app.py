import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
import html
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()
import plotly.graph_objects as go
import anthropic
from datetime import datetime, timedelta

from signal_engine import add_indicators, compute_bias, STOP_LOSS_PCT

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Intelligence Terminal",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# 🎨 FABLE 5 DESIGN SYSTEM — DOCK-V2
#    Ink #0B0E14 · Panel #131824 · Bullion #E8B54A · Signal #37B7C3
#    Long #2FBF71 · Short #E4574C · Display: Space Grotesk (tabular nums)
#    Signature: the gold rail — top nav hairline on desktop,
#    fixed bottom dock on mobile.
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ================= DOCK-V2 · FABLE 5 DESIGN SYSTEM =================
   Layer 6: one token system, one injection, organized by layer.       */
:root {
  --ink: #0B0E14;
  --panel-hi: #151B29;
  --panel-lo: #10141F;
  --bullion: #E8B54A;
  --signal: #37B7C3;
  --volt: #00E5FF;
  --long: #2FBF71;
  --short: #E4574C;
  --watch: #E2A93B;
  --text: #E8ECF3;
  --muted: #97A1B3;
  --edge: rgba(151,161,179,.16);
  --edge-gold: rgba(232,181,74,.18);
}

/* ── Layer 0: canvas & chrome ─────────────────────────────── */
.stApp {
  background:
    radial-gradient(1100px 620px at 88% -12%, rgba(232,181,74,.07), transparent 60%),
    radial-gradient(900px 700px at -10% 112%, rgba(55,183,195,.05), transparent 55%),
    var(--ink);
}
[data-testid="stHeader"] { background: transparent; }
/* ── NATIVE SIDEBAR NAV — Fable 5 skin ───────────────── */
[data-testid="stSidebar"] {
  background: var(--ink);
  border-right: 1px solid rgba(232,181,74,.28);
  box-shadow: 8px 0 24px rgba(0,0,0,.35);
}
[data-testid="stSidebar"] * { font-family: 'Space Grotesk', sans-serif; }
[data-testid="stSidebarNav"] { padding-top: .6rem; }
[data-testid="stSidebarNavLink"] {
  border-radius: 10px;
  margin: 2px 6px;
  color: #C7CEDB !important;
  border: 1px solid transparent;
}
[data-testid="stSidebarNavLink"] span { color: inherit !important; }
[data-testid="stSidebarNavLink"]:hover {
  background: rgba(232,181,74,.1);
  color: var(--text) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(180deg, rgba(232,181,74,.22), rgba(232,181,74,.06));
  border: 1px solid rgba(232,181,74,.45);
  color: var(--bullion) !important;
}
.block-container { padding-top: 1rem; padding-bottom: 1.4rem; max-width: 100%; padding-left: 1.4rem; padding-right: 1.4rem; }

/* ── Layer 1: DENSITY ENGINE — reclaim the vertical dead air ─ */
[data-testid="stVerticalBlock"] { gap: .7rem !important; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important;
             letter-spacing: -0.02em; color: var(--text); }
h1 { font-size: 1.45rem !important; font-weight: 700; margin: 0 !important; padding: .25rem 0 !important; line-height: 1.45 !important; }
h2 { font-size: 1.1rem !important; margin: .35rem 0 !important; padding: 0 !important; line-height: 1.45 !important; }
h3 { font-size: .95rem !important; margin: .3rem 0 !important; padding: 0 !important; line-height: 1.45 !important; }
p, li, span, label { color: #C7CEDB; }
hr { margin: .6rem 0 !important; }
[data-testid="stCaptionContainer"] { margin-bottom: 0 !important; }
[data-testid="stAlert"] { border-radius: 12px; padding: .65rem .95rem !important; line-height: 1.45; }
[data-testid="stAlert"] h3 { margin: 0 0 .15rem 0 !important; }
[data-testid="stExpander"] {
  border: 1px solid var(--edge); border-radius: 12px;
  background: rgba(19,24,36,.55);
}
[data-testid="stExpander"] summary { padding: .5rem .75rem !important; }
[data-testid="stDataFrame"] { border: 1px solid var(--edge); border-radius: 12px; overflow: hidden; }

/* ── Layer 2: PANEL PRIMITIVE — keyed panels are the framing ─ */
[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-panel_"]) {
  border: 1px solid var(--edge-gold) !important;
  border-radius: 16px !important;
  background: linear-gradient(160deg, var(--panel-hi) 0%, var(--panel-lo) 100%) !important;
  box-shadow: 0 8px 22px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.03);
  padding: .7rem .85rem .8rem .85rem;  /* .75rem-class bottom pad: nothing touches frames */
}

/* ── Metrics: compact tiles ──────────────────────────────── */
[data-testid="stMetric"] {
  background: linear-gradient(160deg, var(--panel-hi) 0%, var(--panel-lo) 100%);
  border: 1px solid var(--edge-gold);
  border-radius: 12px;
  padding: .55rem .75rem;
  box-shadow: 0 4px 14px rgba(0,0,0,.28);
}
[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-panel_"]) [data-testid="stMetric"] {
  background: rgba(11,14,20,.35);
  border: 1px solid var(--edge);
  box-shadow: none;
}
[data-testid="stMetricValue"] {
  font-family: 'Space Grotesk', sans-serif;
  font-variant-numeric: tabular-nums;
  font-size: 1.25rem !important;
}
[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  text-transform: uppercase;
  font-size: .64rem !important;
  letter-spacing: .09em;
  line-height: 1.45 !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button, .stDownloadButton > button {
  border-radius: 12px;
  border: 1px solid rgba(232,181,74,.35);
  background: linear-gradient(180deg, rgba(232,181,74,.12), rgba(232,181,74,.03));
  color: var(--text);
  font-family: 'Space Grotesk', sans-serif;
  padding: .3rem .8rem;
  transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}
.stButton > button:hover {
  border-color: rgba(232,181,74,.8);
  box-shadow: 0 0 18px rgba(232,181,74,.18);
  transform: translateY(-1px);
}

/* ── Asset cards ─────────────────────────────────────────── */
.asset-card {
  border-radius: 14px; padding: 14px 12px; text-align: center;
  border: 1px solid transparent;
  background:
    linear-gradient(#141927, #101521) padding-box,
    linear-gradient(150deg, rgba(232,181,74,.55), rgba(232,181,74,.08) 42%, rgba(55,183,195,.28)) border-box;
  box-shadow: 0 8px 20px rgba(0,0,0,.38);
  transition: transform .15s ease, box-shadow .15s ease;
  margin-bottom: 8px;
}
.asset-card:hover { transform: translateY(-2px); box-shadow: 0 12px 26px rgba(0,0,0,.48), 0 0 18px rgba(232,181,74,.12); }
.asset-card.feed-down {
  background: linear-gradient(#141927, #101521) padding-box,
              linear-gradient(150deg, rgba(228,87,76,.6), rgba(228,87,76,.12)) border-box;
}
.ac-name  { font-family:'Space Grotesk'; font-weight:600; font-size:1.05rem; color:var(--text); }
.ac-price { font-family:'Space Grotesk'; font-variant-numeric:tabular-nums;
            font-size:1.15rem; color:var(--bullion); margin:.25rem 0 .1rem 0; }
.ac-pct   { font-weight:600; font-size:.82rem; font-variant-numeric:tabular-nums; }
.ac-pct.up   { color:var(--long); }
.ac-pct.down { color:var(--short); }
.ac-bias  { margin-top:.4rem; font-size:.76rem; color:var(--text); font-weight:600;
            border-top:1px solid var(--edge); padding-top:.4rem; }
.ac-err   { color:var(--short); font-family:'Space Grotesk'; font-size:.95rem; margin:.35rem 0; }
.ac-sub   { color:var(--muted); font-size:.75rem; }

/* ── News cards + tilt badges ───────────────────────────── */
.news-card {
  background: linear-gradient(160deg, var(--panel-hi) 0%, var(--panel-lo) 100%);
  border: 1px solid var(--edge);
  border-radius: 13px;
  padding: 12px 14px;
  margin-bottom: .3rem;
  box-shadow: 0 5px 14px rgba(0,0,0,.28);
}
.nc-title { font-family:'Space Grotesk'; font-size:.9rem; line-height:1.45; }
.nc-title a { color:var(--text) !important; text-decoration:none; }
.nc-title a:hover { color:var(--bullion) !important; }
.nc-meta { color:var(--muted); font-size:.7rem; margin-top:.4rem; }
.tilt {
  display:inline-block; padding:2px 9px; border-radius:8px;
  font-size:.66rem; font-weight:700; letter-spacing:.05em;
  font-family:'Space Grotesk';
}
.tilt.bullish { background:rgba(47,191,113,.14); color:var(--long); border:1px solid rgba(47,191,113,.4); }
.tilt.bearish { background:rgba(228,87,76,.14); color:var(--short); border:1px solid rgba(228,87,76,.4); }
.tilt.neutral { background:rgba(151,161,179,.14); color:var(--muted); border:1px solid rgba(151,161,179,.4); }

/* ── Macro event rows ───────────────────────────────────── */
.macro-row {
  display:flex; align-items:center; gap:.7rem; flex-wrap:wrap;
  padding:.45rem .7rem; margin-bottom:.35rem; border-radius:11px;
  background: rgba(11,14,20,.35);
  border:1px solid var(--edge);
}
.mr-when { display:flex; align-items:center; gap:.45rem; min-width:135px; }
.cur-badge {
  font-family:'Space Grotesk'; font-weight:700; font-size:.66rem;
  padding:2px 7px; border-radius:7px;
  background:rgba(232,181,74,.14); color:var(--bullion);
  border:1px solid rgba(232,181,74,.35);
}
.mr-time { color:var(--muted); font-size:.74rem; font-variant-numeric:tabular-nums; }
.mr-event { flex:1 1 180px; color:var(--text); font-size:.84rem; }
.mr-nums { color:var(--muted); font-size:.72rem; font-variant-numeric:tabular-nums; }
.chip {
  padding:2px 8px; border-radius:8px; font-size:.64rem; font-weight:700;
  font-family:'Space Grotesk'; white-space:nowrap;
}
.chip.up  { background:rgba(226,169,59,.14); color:var(--watch); border:1px solid rgba(226,169,59,.4); }
.chip.rel { background:rgba(151,161,179,.12); color:var(--muted); border:1px solid rgba(151,161,179,.3); }

/* ── Trade log rows ─────────────────────────────────────── */
.trade-row {
  display:flex; justify-content:space-between; align-items:center;
  gap:.7rem; flex-wrap:wrap;
  padding:.45rem .7rem; margin-bottom:.3rem; border-radius:11px;
  background: rgba(11,14,20,.35);
  border:1px solid var(--edge);
  border-left:3px solid;
}
.trade-row.win  { border-left-color:var(--long); }
.trade-row.loss { border-left-color:var(--short); }
.tr-type   { color:var(--text); font-size:.8rem; font-weight:600; margin-right:.5rem; }
.tr-dates, .tr-prices { color:var(--muted); font-size:.71rem; font-variant-numeric:tabular-nums; }
.ret-badge {
  font-family:'Space Grotesk'; font-weight:700; font-size:.76rem;
  padding:2px 9px; border-radius:8px; font-variant-numeric:tabular-nums;
}
.ret-badge.win  { background:rgba(47,191,113,.14); color:var(--long); }
.ret-badge.loss { background:rgba(228,87,76,.14); color:var(--short); }

/* ── Strategy matrix cards ──────────────────────────────── */
.strat-card {
  border-radius:13px; padding:12px 10px; text-align:center;
  border:1px solid var(--edge);
  background:linear-gradient(160deg,var(--panel-hi),var(--panel-lo));
  margin-bottom:.4rem;
}
.strat-card.selected { border:1px solid rgba(232,181,74,.55); box-shadow:0 0 16px rgba(232,181,74,.15); }
.sc-name { font-family:'Space Grotesk'; font-weight:600; color:var(--text); font-size:.9rem; }
.sc-verdict { font-size:.72rem; margin:.25rem 0; font-weight:700; font-family:'Space Grotesk'; }
.sc-verdict.good { color:var(--long); }
.sc-verdict.mid  { color:var(--watch); }
.sc-verdict.bad  { color:var(--short); }
.sc-line { color:var(--muted); font-size:.7rem; font-variant-numeric:tabular-nums; }

/* ── STATIC SHOCK LAYER ⚡ — volt is the SECONDARY accent:
   engine-core titles, execution frames, AI borders, the init card. ─ */
.volt-title {
  font-family:'Space Grotesk'; font-weight:700; font-size:.72rem;
  letter-spacing:.13em; color:var(--volt);
  text-shadow:0 0 10px rgba(0,229,255,.55);
  margin-bottom:.5rem;
  padding-bottom:.15rem;
  line-height:1.45;
}
.shock-card {
  border-radius:16px; padding:.9rem 1rem; text-align:center;
  border:1px solid rgba(0,229,255,.45);
  background:linear-gradient(160deg, rgba(0,229,255,.08), rgba(16,20,31,.75));
  box-shadow:0 0 26px rgba(0,229,255,.14), inset 0 0 30px rgba(0,229,255,.05);
}
.shock-title {
  font-family:'Space Grotesk'; font-weight:700; font-size:1.1rem;
  color:var(--text); letter-spacing:.05em;
  text-shadow:0 0 14px rgba(0,229,255,.6);
}
.shock-sub { color:var(--muted); font-size:.76rem; margin-top:.35rem; line-height:1.45; }
/* Execution panel gets the voltage frame */
[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-panel_actions) {
  border: 1px solid rgba(0,229,255,.35) !important;
  box-shadow: 0 0 18px rgba(0,229,255,.1), inset 0 1px 0 rgba(255,255,255,.03) !important;
}
/* AI response frames */
[data-testid="stChatMessage"] {
  border: 1px solid rgba(0,229,255,.3);
  border-radius: 14px;
  background: rgba(0,229,255,.04);
}
/* Sidebar brand */
[data-testid="stSidebarNav"]::before {
  content: "⚡ STATIC SHOCK";
  display: block;
  padding: .55rem 1rem .35rem 1rem;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: .72rem;
  letter-spacing: .15em;
  color: var(--volt);
  text-shadow: 0 0 10px rgba(0,229,255,.55);
}

/* ── INFINITE TICKER TAPE ─────────────────────────── */
.tape-wrap {
  overflow: hidden;
  border-top: 1px solid rgba(0,229,255,.25);
  border-bottom: 1px solid rgba(232,181,74,.28);
  background: linear-gradient(160deg, rgba(21,27,41,.7), rgba(16,20,31,.7));
  border-radius: 10px;
}
.tape {
  display: inline-flex; align-items: baseline; gap: 1.6rem;
  padding: .38rem 0;
  white-space: nowrap;
  will-change: transform;
  animation: marquee 36s linear infinite;
}
.tape:hover { animation-play-state: paused; }
@keyframes marquee {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.tp-item { display: inline-flex; align-items: baseline; gap: .45rem;
           font-variant-numeric: tabular-nums; }
.tp-sym { font-family:'Space Grotesk'; font-weight:700; font-size:.74rem; color:var(--muted); }
.tp-px  { font-family:'Space Grotesk'; font-size:.84rem; color:var(--text); }
.tp-pct { font-size:.74rem; font-weight:600; }
.tp-pct.up { color:var(--long); } .tp-pct.down { color:var(--short); }
.tp-dead { color:var(--short); font-size:.74rem; }
.tp-sep { color: var(--volt); text-shadow: 0 0 8px rgba(0,229,255,.5);
          font-size:.7rem; margin: 0 .2rem; }

/* ── MACRO WEEK TRACK — fixed-height horizontal strip ───── */
.macro-track {
  display: flex; gap: .5rem;
  overflow-x: auto; overflow-y: hidden;
  padding: .25rem .1rem .45rem .1rem;
  scrollbar-width: thin;
}
.macro-cardlet {
  flex: 0 0 auto; min-width: 200px; max-width: 250px;
  border: 1px solid var(--edge);
  border-radius: 12px; padding: .45rem .65rem;
  background: linear-gradient(160deg, var(--panel-hi), var(--panel-lo));
}
.mc-top { display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
.mc-event {
  color: var(--text); font-size: .78rem; margin: .2rem 0 .1rem 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ── Layer 4a: MOBILE BOTTOM DOCK ONLY — desktop nav is the
   NATIVE Streamlit sidebar (framework-guaranteed clickable).
   The dock is position:fixed (zero-height parents) with pointer
   armor as defense-in-depth. ─────────────────────────── */
.st-key-bottomnav {
  display: none;
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 60;
  background: rgba(11,14,20,.95);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border-top: 1px solid rgba(232,181,74,.3);
  padding: .25rem .3rem calc(.25rem + env(safe-area-inset-bottom)) .3rem;
  flex-direction: row !important; flex-wrap: nowrap !important;
  gap: .15rem !important; align-items: stretch !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-bottomnav),
[data-testid="stElementContainer"]:has(.st-key-bottomnav),
div:has(> .st-key-bottomnav) {
  pointer-events: none !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  min-height: 0 !important;
}
.st-key-bottomnav { pointer-events: none !important; }
.st-key-bottomnav a { pointer-events: auto !important; }
.st-key-bottomnav [data-testid="stVerticalBlock"] {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  gap: .15rem !important;
  align-items: stretch !important;
}
.st-key-bottomnav > div,
.st-key-bottomnav [data-testid="stElementContainer"] {
  width: auto !important; min-width: 0 !important;
  flex: 1 1 0 !important;
}
.st-key-bottomnav a {
  display: flex !important; align-items: center; justify-content: center;
  width: 100%;
  border-radius: 10px;
  padding: .3rem .4rem !important;
  color: #C7CEDB !important;
  text-decoration: none !important;
  font-family: 'Space Grotesk', sans-serif;
  font-size: .84rem;
  white-space: nowrap;
  border: 1px solid transparent;
}
.st-key-bottomnav a:hover {
  background: rgba(232,181,74,.1); color: var(--text) !important;
}
.st-key-bottomnav a[aria-current="page"] {
  background: linear-gradient(180deg, rgba(232,181,74,.22), rgba(232,181,74,.06));
  border: 1px solid rgba(232,181,74,.45);
  color: var(--bullion) !important;
}

/* ── Gateway: pulse bar, marquee, health dots ─────────── */
.pulse-bar { display:flex; gap:.5rem; flex-wrap:wrap; }
.pulse-chip {
  display:flex; align-items:baseline; gap:.5rem;
  padding:.35rem .8rem; border-radius:11px;
  background:linear-gradient(160deg,var(--panel-hi),var(--panel-lo));
  border:1px solid var(--edge);
  font-variant-numeric:tabular-nums;
}
.pc-name { font-family:'Space Grotesk'; font-weight:700; font-size:.74rem; color:var(--muted); }
.pc-px { font-family:'Space Grotesk'; font-size:.86rem; color:var(--text); }
.pc-pct { font-size:.74rem; font-weight:600; }
.pc-pct.up { color:var(--long); } .pc-pct.down { color:var(--short); }
.pulse-chip.dead { border-color:rgba(228,87,76,.4); }
.pc-dead { color:var(--short); font-size:.74rem; }
.marquee {
  border-radius:14px; padding:.7rem .9rem;
  border:1px solid rgba(226,169,59,.45);
  background:linear-gradient(160deg, rgba(226,169,59,.1), rgba(16,20,31,.6));
}
.mq-label { font-family:'Space Grotesk'; font-weight:700; font-size:.66rem;
            letter-spacing:.1em; color:var(--watch); }
.mq-event { font-family:'Space Grotesk'; font-size:1rem; color:var(--text); margin:.15rem 0; }
.mq-meta  { color:var(--muted); font-size:.76rem; font-variant-numeric:tabular-nums; }
.health-row { display:flex; align-items:center; gap:.55rem; padding:.35rem 0;
              color:var(--text); font-size:.84rem; line-height:1.45; }
.dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
.dot.ok   { background:var(--long); box-shadow:0 0 8px rgba(47,191,113,.6); }
.dot.warn { background:var(--watch); box-shadow:0 0 8px rgba(226,169,59,.6); }
.dot.err  { background:var(--short); box-shadow:0 0 8px rgba(228,87,76,.6); }
.health-sub { color:var(--muted); font-size:.7rem; margin-left:auto; }

/* ── Layer 4b: RESPONSIVE SPLIT — ≤768px = phone ergonomics ─ */
@media (max-width: 640px) {
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
  .st-key-bottomnav { display: flex !important; }
  [data-testid="stHeader"] { display: none; }
  .block-container {
    padding-left: .8rem; padding-right: .8rem; padding-top: .6rem;
    padding-bottom: calc(4.8rem + env(safe-area-inset-bottom));
  }
  /* Fixed-height panels collapse to natural height, capped, no clipping */
  [data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-panel_"]) {
    height: auto !important; max-height: 65vh; overflow-y: auto;
  }
  h1 { font-size: 1.25rem !important; }
  [data-testid="stMetricValue"] { font-size: 1.05rem !important; }
  [data-testid="stMetricLabel"] { font-size: .58rem !important; }
  /* ── 2-UP PHONE GRID: keep column pairs side-by-side instead of
     stacking every metric into a full-width slab. Halves the scroll,
     evens the composition. 3-col rows wrap 2+1. ── */
  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: .5rem !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    flex: 1 1 46% !important;
    min-width: 46% !important;
    width: auto !important;
  }
  /* Raise the content into the dead space up top */
  .block-container {
    padding-top: .35rem !important;
    padding-bottom: calc(6rem + env(safe-area-inset-bottom)) !important;
  }
  h1 { padding: .1rem 0 !important; }
  .volt-title { margin-bottom: .35rem !important; }
  [data-testid="stMetric"] { padding: .45rem .6rem !important; }
  [data-testid="stAlert"] { padding: .55rem .8rem !important; }
  /* ── DOCK v2: bigger targets, icon-forward, dimmed inactive ── */
  .st-key-bottomnav { padding-top: .3rem !important; }
  .st-key-bottomnav a {
    flex-direction: column !important;
    gap: 3px;
    min-height: 52px;
    padding: .28rem .05rem !important;
    border-radius: 12px;
    color: #7E8798 !important;
  }
  .st-key-bottomnav a > span:first-of-type { font-size: 1.45rem; line-height: 1; }
  .st-key-bottomnav a p, .st-key-bottomnav a span:not(:first-of-type) {
    font-size: .58rem !important; margin: 0 !important; line-height: 1.1;
  }
  .st-key-bottomnav a[aria-current="page"] {
    box-shadow: none;
    color: var(--bullion) !important;
  }
  /* Every button becomes a real thumb target */
  .stButton > button, .stDownloadButton > button {
    min-height: 46px !important;
    font-size: .95rem !important;
  }
  /* Form inputs hit the 44px Apple floor */
  [data-baseweb="select"] > div,
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input,
  [data-testid="stDateInput"] input {
    min-height: 44px !important;
  }
  /* Cards and rows stay readable + tappable */
  .asset-card { padding: 12px 12px !important; }
  .macro-cardlet { min-width: 220px; padding: .6rem .75rem; }
  .trade-row, .macro-row { padding: .6rem .8rem; }
  [data-testid="stVerticalBlock"] { gap: .65rem !important; }
}
@media (min-width: 641px) {
  .st-key-bottomnav { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Anthropic client: fail loudly, once, at startup ─────────
API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=API_KEY) if API_KEY else None


# =====================================================================
# 📋 WATCHLIST — single source of truth shared with the alert bot
# =====================================================================
WATCHLIST_FILE = "watchlist.json"
DEFAULT_WATCHLIST = {
    "Gold": {"ticker": "GC=F", "name": "Gold Market", "unit": "/oz"},
    "S&P 500": {"ticker": "^GSPC", "name": "S&P 500 Index", "unit": ""},
    "SOFI": {"ticker": "SOFI", "name": "SoFi Technologies", "unit": "/sh"}
}


def load_watchlist_from_disk():
    try:
        with open(WATCHLIST_FILE) as f:
            wl = json.load(f)
        if isinstance(wl, dict) and wl:
            return wl
    except Exception:
        pass
    return dict(DEFAULT_WATCHLIST)


def save_watchlist_to_disk(wl: dict) -> bool:
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(wl, f, indent=2)
        return True
    except Exception:
        return False


if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist_from_disk()

if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}


def get_watchlist() -> dict:
    return st.session_state.watchlist


def asset_picker():
    """Compact asset switcher rendered at the top of every analysis page.
    Selection persists across pages via session_state.active_asset."""
    wl = list(get_watchlist().keys())
    cur = st.session_state.get("active_asset", wl[0])
    if cur not in wl:
        cur = wl[0]
    left, right = st.columns([5, 2])
    with right:
        sel = st.selectbox("Asset", wl, index=wl.index(cur),
                           key="_asset_picker", label_visibility="collapsed")
    st.session_state.active_asset = sel
    return sel, left


def get_selected_asset():
    wl = get_watchlist()
    sel = st.session_state.get("active_asset")
    if sel in wl:
        return sel
    return list(wl.keys())[0]


# =====================================================================
# 🔧 SHARED HELPERS
# =====================================================================
def md_safe(text: str) -> str:
    """Escape $ so Streamlit markdown doesn't treat prices as LaTeX."""
    return text.replace("$", "\\$")


@st.cache_data(ttl=60)
def load_market_data(ticker):
    """Daily OHLC + indicator columns via the shared signal engine."""
    end = datetime.today()
    start = end - timedelta(days=1825)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close"]].astype(float).copy()
    df = df.rename(columns={"Close": "Price"})
    return add_indicators(df)


@st.cache_data(ttl=120)
def fetch_portal_quote(ticker):
    """
    Robust quote fetch with fallback. Returns (price, change, pct) or None.
    NEVER fabricates a $0.00 quote — a dead feed must look dead.
    """
    try:
        df = yf.download(ticker, period="1mo", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        closes = df["Close"].dropna().astype(float)
        if len(closes) >= 2:
            c, p = float(closes.iloc[-1]), float(closes.iloc[-2])
            return c, c - p, ((c - p) / p) * 100
    except Exception:
        pass

    try:
        fi = yf.Ticker(ticker).fast_info
        c = float(fi["last_price"])
        p = float(fi["previous_close"])
        return c, c - p, ((c - p) / p) * 100
    except Exception:
        return None


# =====================================================================
# 📊 BACKTEST ENGINE — multi-strategy matrix (Phase 6)
#    Every strategy runs the same honest execution model:
#    signals on the close → fills at the NEXT bar's open,
#    intraday stop checks with gap handling, compounded equity.
# =====================================================================
STRATEGIES = {
    "meanrev": {
        "name": "Mean Reversion",
        "desc": "Band touch WITH the 200 EMA trend → revert to the 20 EMA",
    },
    "breakout": {
        "name": "Momentum Breakout",
        "desc": "Band break WITH the 200 EMA trend → ride until the 20 EMA gives up",
    },
    "rsi": {
        "name": "RSI Reversion",
        "desc": "RSI(14) below 30 / above 70 with the trend filter → exit at RSI 50",
    },
}


@st.cache_data(ttl=300)
def run_backtest(ticker, asset_name, strategy="meanrev"):
    df = load_market_data(ticker)
    valid = df.dropna(subset=["Upper_Band", "Lower_Band", "Baseline", "Macro_Filter"]).copy()

    # RSI(14), Wilder smoothing — used by the rsi strategy
    delta = valid["Price"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    valid["RSI"] = 100 - 100 / (1 + rs)

    equity = 1.0
    equity_marks = [1.0]
    position = 0
    entry_price = 0.0
    entry_date = None
    pending_entry = 0
    pending_exit_label = None
    trades = []

    def close_trade(exit_price, exit_date, label):
        nonlocal equity, position, entry_price, entry_date, pending_exit_label
        if position == 1:
            trade_return = (exit_price - entry_price) / entry_price
        else:
            trade_return = (entry_price - exit_price) / entry_price
        equity *= (1 + trade_return)
        equity_marks.append(equity)
        trades.append({
            "Asset": asset_name,
            "Type": label,
            "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Exit Date": exit_date.strftime("%Y-%m-%d"),
            "Entry Price": f"${entry_price:,.2f}",
            "Exit Price": f"${exit_price:,.2f}",
            "Return": f"{trade_return * 100:+.2f}%",
            "_ret": trade_return,
            "_dir": "long" if position == 1 else "short",
        })
        position = 0
        entry_price = 0.0
        entry_date = None
        pending_exit_label = None

    for bar in valid.itertuples():
        open_ = float(bar.Open)
        high = float(bar.High)
        low = float(bar.Low)
        close = float(bar.Price)
        baseline_v = float(bar.Baseline)
        upper_v = float(bar.Upper_Band)
        lower_v = float(bar.Lower_Band)
        macro_v = float(bar.Macro_Filter)
        rsi_v = None if pd.isna(bar.RSI) else float(bar.RSI)

        # 1) Fill pending entry at this bar's open
        if position == 0 and pending_entry != 0:
            position = pending_entry
            entry_price = open_
            entry_date = bar.Index
            pending_entry = 0
        # 2) Fill pending signal exit at this bar's open
        elif position != 0 and pending_exit_label is not None:
            close_trade(open_, bar.Index, pending_exit_label)

        # 3) Intraday stop check (gaps fill at the open)
        if position == 1:
            stop = entry_price * (1 - STOP_LOSS_PCT)
            if low <= stop:
                close_trade(min(open_, stop), bar.Index, "Long (Stop Loss Hit)")
        elif position == -1:
            stop = entry_price * (1 + STOP_LOSS_PCT)
            if high >= stop:
                close_trade(max(open_, stop), bar.Index, "Short (Stop Loss Hit)")

        # 4) Exit signals on the close → fill next open
        if position == 1:
            if (strategy == "meanrev" and close >= baseline_v) or \
               (strategy == "breakout" and close < baseline_v) or \
               (strategy == "rsi" and rsi_v is not None and rsi_v >= 50):
                pending_exit_label = "Long Exit (Signal)"
        elif position == -1:
            if (strategy == "meanrev" and close <= baseline_v) or \
               (strategy == "breakout" and close > baseline_v) or \
               (strategy == "rsi" and rsi_v is not None and rsi_v <= 50):
                pending_exit_label = "Short Exit (Signal)"

        # 5) Entry signals on the close → fill next open
        if position == 0 and pending_entry == 0:
            if strategy == "meanrev":
                if close < lower_v and close > macro_v:
                    pending_entry = 1
                elif close > upper_v and close < macro_v:
                    pending_entry = -1
            elif strategy == "breakout":
                if close > upper_v and close > macro_v:
                    pending_entry = 1
                elif close < lower_v and close < macro_v:
                    pending_entry = -1
            elif strategy == "rsi":
                if rsi_v is not None:
                    if rsi_v < 30 and close > macro_v:
                        pending_entry = 1
                    elif rsi_v > 70 and close < macro_v:
                        pending_entry = -1

    def stat_block(subset):
        rets = [t["_ret"] for t in subset]
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        return {
            "n": len(rets),
            "win_rate": (len(wins) / len(rets)) if rets else 0.0,
            "avg_win": float(np.mean(wins)) if wins else 0.0,
            "avg_loss": float(np.mean(losses)) if losses else 0.0,
        }

    eq = np.array(equity_marks)
    running_max = np.maximum.accumulate(eq)
    drawdowns = (eq - running_max) / running_max
    first = float(valid["Price"].iloc[0])
    last = float(valid["Price"].iloc[-1])

    stats = {
        "strategy_return": equity - 1.0,
        "buy_hold_return": (last - first) / first,
        "max_drawdown": float(drawdowns.min()) if len(eq) > 1 else 0.0,
        "all": stat_block(trades),
        "long": stat_block([t for t in trades if t["_dir"] == "long"]),
        "short": stat_block([t for t in trades if t["_dir"] == "short"]),
    }
    display_trades = [{k: v for k, v in t.items() if not k.startswith("_")} for t in trades]
    return display_trades, stats


def viability(stats):
    """STRATEGY VIABILITY verdict from profit factor + per-trade expectancy."""
    s = stats["all"]
    n, wr, aw, al = s["n"], s["win_rate"], s["avg_win"], s["avg_loss"]
    expectancy = wr * aw + (1 - wr) * al
    gross_win = wr * aw
    gross_loss = abs((1 - wr) * al)
    if gross_loss > 0:
        pf = gross_win / gross_loss
    else:
        pf = float("inf") if gross_win > 0 else 0.0
    if n < 15:
        return "⚠️ INSUFFICIENT SAMPLE", "mid", pf, expectancy
    if pf >= 1.3 and expectancy > 0:
        return "✅ VIABLE EDGE", "good", pf, expectancy
    if pf >= 0.9:
        return "🟡 COIN-FLIP — NO EDGE", "mid", pf, expectancy
    return "❌ NOT VIABLE", "bad", pf, expectancy


# =====================================================================
# 🚨 MACRO CALENDAR — Forex Factory weekly JSON feed (Phase 3)
#    Primary: FF's official this-week JSON (includes FUTURE events with
#    timestamps). Fallback: HTML scrape. Never blanks if the week has
#    scheduled high-impact releases still ahead.
# =====================================================================
@st.cache_data(ttl=1800)
def fetch_macro_calendar():
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        et = None

    events = []
    # ── Primary: official weekly JSON feed ──
    try:
        r = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=8
        )
        if r.status_code == 200:
            now_utc = datetime.now().astimezone()
            for e in r.json():
                if str(e.get("impact", "")).lower() != "high":
                    continue
                dt = None
                try:
                    dt = datetime.fromisoformat(e.get("date", ""))
                except Exception:
                    pass
                upcoming = bool(dt and dt >= now_utc)
                when = "—"
                if dt is not None:
                    local = dt.astimezone(et) if et else dt
                    when = local.strftime("%a %I:%M %p")
                events.append({
                    "Time (ET)": when,
                    "Currency": e.get("country", "?"),
                    "Event": e.get("title", "?"),
                    "Forecast": e.get("forecast") or "N/A",
                    "Previous": e.get("previous") or "N/A",
                    "Status": "⏳ Upcoming" if upcoming else "✔ Released",
                    "_ts": dt.timestamp() if dt else 9e12,
                    "_up": upcoming,
                })
            events.sort(key=lambda x: (not x["_up"], x["_ts"]))
            for ev in events:
                ev.pop("_ts", None); ev.pop("_up", None)
            if events:
                return events
    except Exception:
        pass

    # ── Fallback: scrape the calendar page (no times available) ──
    try:
        response = requests.get(
            "https://www.forexfactory.com/calendar",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"},
            timeout=5
        )
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "lxml")
        for row in soup.find_all("tr", class_="calendar__row"):
            impact_cell = row.find("td", class_="calendar__impact")
            if impact_cell and impact_cell.find("span", class_="icon--impact-high"):
                currency_el = row.find("td", class_="calendar__currency")
                event_el = row.find("td", class_="calendar__event")
                forecast_el = row.find("td", class_="calendar__forecast")
                if currency_el and event_el:
                    events.append({
                        "Time (ET)": "—",
                        "Currency": currency_el.get_text(strip=True),
                        "Event": event_el.get_text(strip=True),
                        "Forecast": (forecast_el.get_text(strip=True) if forecast_el else "") or "N/A",
                        "Previous": "N/A",
                        "Status": "—",
                    })
        return events[:10]
    except Exception:
        return []


@st.cache_data(ttl=1800)
def fetch_news_items(ticker):
    """Full RSS items — title, link, published time — for the card gallery."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml-xml")
        items = []
        for it in soup.find_all("item")[:8]:
            title = it.title.get_text(strip=True) if it.title else ""
            if len(title) < 20:
                continue
            items.append({
                "title": title,
                "link": it.link.get_text(strip=True) if it.link else "",
                "published": it.pubDate.get_text(strip=True) if it.pubDate else "",
            })
        return items
    except Exception:
        return []


# =====================================================================
# 🤖 CACHED AI CALLS (all fire on-demand via buttons)
# =====================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def ai_bias_memo(_client, name, ticker, bias_snapshot, stats_snapshot, macro_snapshot):
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        messages=[{
            "role": "user",
            "content": f"""You are a cynical institutional quantitative risk manager. A retail trader's dashboard has computed the statistical state below for {name} ({ticker}). Your job is to interpret it coldly — no encouragement, no hedging into vagueness. Base rates and math only.

Current Statistical State:
{bias_snapshot}

5-Year Backtest Base Rates for this exact setup (next-bar fills, compounded):
{stats_snapshot}

High-Impact Macro Events This Week:
{macro_snapshot}

Write a tight memo with exactly these sections:
1. BIAS VERDICT: One sentence — does the statistical evidence support acting right now, or standing aside?
2. EVIDENCE WEIGHING: 3 bullets max — which numbers above carry the verdict and which are noise.
3. WHAT WOULD CHANGE THE CALL: The exact price levels or macro events that flip or kill this bias.
4. BASE RATE REALITY CHECK: One sentence contrasting the trader's likely expectation with the historical win rate and avg win/loss.

This is statistical interpretation, not financial advice. Be direct."""
        }]
    )
    return response.content[0].text


@st.cache_data(ttl=1800, show_spinner=False)
def ai_news_analysis(_client, name, ticker, headline_block):
    """One call, everything: overall sentiment + a per-headline macro read.
    Returns a dict; falls back to {"raw": text} if JSON parsing fails."""
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=900,
        messages=[{
            "role": "user",
            "content": f"""You are a senior market analyst. Analyze these numbered financial headlines for {name} ({ticker}).

Headlines:
{headline_block}

Respond with ONLY a JSON object, no markdown fences, no preamble, in exactly this shape:
{{"overall": {{"sentiment": "Bullish|Bearish|Neutral", "score": <integer -10 to 10>, "summary": "<2 sentences on short-term price direction>"}}, "impacts": [{{"i": <headline number>, "tilt": "bullish|bearish|neutral", "impact": "<one sentence: the macro effect of this headline on {name}>"}}]}}

Include one impacts entry per headline. Be concise and direct."""
        }]
    )
    text = response.content[0].text.strip()
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {"raw": text}


QUICK_PROMPTS = [
    "Explain the current sentiment in simple terms",
    "What structural level signals a bad/good trade setup right now?",
    "Summarize the risk here for a beginner",
    "Is now statistically a good time to enter? Why or why not?",
]


@st.cache_data(ttl=900, show_spinner=False)
def ai_quick_answer(_client, question, name, ticker, context):
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""You are a quantitative analyst explaining a trading terminal readout for {name} ({ticker}) to its owner. Answer their question plainly, in simple language, using ONLY the numbers below. 3-5 sentences max. End with one sentence noting this is statistical interpretation, not financial advice.

Live terminal readout:
{context}

Question: {question}"""
        }]
    )
    return response.content[0].text


@st.cache_data(ttl=900, show_spinner=False)
def ai_stress_test(_client, asset_name, trade_key, days_left, price_bucket,
                   market_snapshot, stats_snapshot):
    trade = st.session_state.active_trades[asset_name]
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"""You are a cynical, strict institutional quantitative risk manager. Aggressively stress-test this retail trader's options thesis using hard data and math. Do not encourage them or validate their biases.

Position Parameters:
- Type: {trade['Type']}
- Strike: ${trade['Strike']}
- Time Horizon: {days_left} days until expiration
- Entry Premium Paid: ${trade['Entry Premium']}
- Trader's Narrative/Thesis: {trade['Thesis']}

Current Statistical Market Realities for {asset_name}:
{market_snapshot}

Historical Base Rates for this setup (5yr backtest, next-bar fills, compounded):
{stats_snapshot}

Provide a critical, data-driven cross-examination structured exactly as follows:
1. DATA-DRIVEN THESIS STRESS-TEST: Use spot vs 20 EMA and the volatility bands to challenge the core logic.
2. MATHEMATICAL HURDLE: Exact % move needed to break even given premium vs strike, contrasted with the {days_left}-day window.
3. HISTORICAL BASE RATE CHECK: Judge the thesis against the backtest win rate, avg win/loss, and max drawdown.
4. ASSUMPTION STACK: List every implicit assumption that must go perfectly for this option not to expire worthless.
5. CONCRETE RISK CUTOFF: An explicit stop-loss price or time-decay boundary where this trade is structurally dead."""
        }]
    )
    return response.content[0].text


def require_client(feature: str) -> bool:
    if client is None:
        st.error(f"⚠️ ANTHROPIC_API_KEY missing — {feature} is disabled until it's set in your .env file (or Streamlit Cloud Secrets).")
        return False
    return True


PULSE_TICKERS = {"SPY": "SPY", "QQQ": "QQQ", "GLD": "GLD", "BTC": "BTC-USD",
                 "AAPL": "AAPL", "NVDA": "NVDA", "TSLA": "TSLA"}

# Landing-page market trackers: context instruments, NOT scan pipelines —
# quote-only (no bias computation) to keep the Briefing's load instant.
MARKET_TRACKERS = {
    "SPCX": ("SPCX", "SPAC ETF"),
    "QQQ": ("QQQ", "Invesco QQQ Trust"),
    "TLT": ("TLT", "20+ Yr Treasury ETF"),
}


def get_secret(key):
    v = os.getenv(key)
    if v:
        return v
    try:
        return st.secrets[key]
    except Exception:
        return None


def send_telegram_out(message: str):
    """Outbound dispatch to the Telegram pipeline.
    Returns True on send, False on API failure, None if unconfigured."""
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat_id = get_secret("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4000]},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def read_bot_status():
    """Alert-bot heartbeat from signal_state.json (committed by the cloud bot)."""
    try:
        with open("signal_state.json") as f:
            state = json.load(f)
        stamps = [v.get("checked_at") for k, v in state.items()
                  if not k.startswith("_") and isinstance(v, dict) and v.get("checked_at")]
        if not stamps:
            return "warn", "state file empty"
        latest = max(stamps)
        dt = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ")
        age_min = (datetime.utcnow() - dt).total_seconds() / 60
        if age_min <= 90:
            return "ok", f"last check {int(age_min)}m ago"
        return "warn", f"last check {int(age_min)}m ago"
    except Exception:
        return "warn", "no state file in this deploy"


def render_macro_events(events):
    """Macro calendar as styled event rows (mobile-safe: rows flex-wrap)."""
    for e in events:
        status = e.get("Status", "")
        if status.startswith("⏳"):
            chip = '<span class="chip up">⏳ Upcoming</span>'
        elif status.startswith("✔"):
            chip = '<span class="chip rel">✔ Released</span>'
        else:
            chip = ''
        nums = f"F {html.escape(str(e.get('Forecast', 'N/A')))} · P {html.escape(str(e.get('Previous', 'N/A')))}"
        st.markdown(
            f"""
            <div class="macro-row">
                <div class="mr-when">
                    <span class="cur-badge">{html.escape(str(e.get('Currency', '?')))}</span>
                    <span class="mr-time">{html.escape(str(e.get('Time (ET)', '—')))}</span>
                </div>
                <div class="mr-event">{html.escape(str(e.get('Event', '?')))}</div>
                <div class="mr-nums">{nums}</div>
                {chip}
            </div>
            """,
            unsafe_allow_html=True
        )


def render_macro_track(events, limit=10):
    """Fixed-height horizontal macro strip — scrolls sideways, never pushes
    lower page modules down. Thumb-swipes naturally on mobile."""
    cards = []
    for e in events[:limit]:
        status = str(e.get("Status", ""))
        if status.startswith("⏳"):
            chip = '<span class="chip up">⏳ Upcoming</span>'
        elif status.startswith("✔"):
            chip = '<span class="chip rel">✔ Released</span>'
        else:
            chip = ''
        cards.append(
            f"""<div class="macro-cardlet">
                <div class="mc-top"><span class="cur-badge">{html.escape(str(e.get('Currency','?')))}</span>
                <span class="mr-time">{html.escape(str(e.get('Time (ET)','—')))}</span>{chip}</div>
                <div class="mc-event">{html.escape(str(e.get('Event','?')))}</div>
                <div class="mr-nums">F {html.escape(str(e.get('Forecast','N/A')))} · P {html.escape(str(e.get('Previous','N/A')))}</div>
            </div>"""
        )
    st.markdown(f'<div class="macro-track">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_trade_log(trades, limit=20):
    """Trade log as win/loss-colored rows; full table tucked in an expander."""
    if not trades:
        st.info("No trades matched this strategy's parameters in the window.")
        return
    recent = list(reversed(trades))[:limit]
    for t in recent:
        win = str(t.get("Return", "")).startswith("+")
        cls = "win" if win else "loss"
        st.markdown(
            f"""
            <div class="trade-row {cls}">
                <div><span class="tr-type">{html.escape(str(t.get('Type', '')))}</span>
                     <span class="tr-dates">{html.escape(str(t.get('Entry Date', '')))} → {html.escape(str(t.get('Exit Date', '')))}</span></div>
                <div><span class="tr-prices">{html.escape(str(t.get('Entry Price', '')))} → {html.escape(str(t.get('Exit Price', '')))}</span>
                     <span class="ret-badge {cls}">{html.escape(str(t.get('Return', '')))}</span></div>
            </div>
            """,
            unsafe_allow_html=True
        )
    if len(trades) > limit:
        with st.expander(f"Full log — all {len(trades)} trades"):
            st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)


# =====================================================================
# PAGE 1: 🎛️ GLOBAL BRIEFING — the Terminal Entry Gateway
# =====================================================================
def page_command_center():
    wl = get_watchlist()

    # ⚡ GB-LOCAL de-suffocation — injected here, so these rules exist ONLY
    # while the Global Briefing renders. Other pages keep their tuned density.
    st.markdown("""
    <style>
    /* GB-LOCAL: de-suffocation, active only while this page is rendered */
    h1, h2, h3, .volt-title, .mq-label, .gb-title {
        line-height: 1.5 !important;
        padding-bottom: .4rem !important;
    }
    .mq-event, .tp-item, .tp-sym, .tp-px, .tp-pct,
    .ac-name, .ac-price, .ac-pct, .ac-bias, .ac-sub {
        line-height: 1.5 !important;
    }
    [data-testid="stVerticalBlock"] { gap: .85rem !important; }
    .asset-card { padding: 10px 14px !important; }
    .asset-card .ac-bias { padding-top: .45rem !important; }
    .tape-wrap { margin: .45rem 0 .9rem 0 !important; }
    .marquee { margin-bottom: .9rem !important; }
    .health-row { padding: .42rem 0 !important; }
    .gb-head {
        display: flex; align-items: baseline; gap: .8rem;
        padding: .1rem .1rem 0 .1rem;
    }
    .gb-title {
        font-family: 'Space Grotesk', sans-serif; font-weight: 700;
        font-size: 1.25rem; color: var(--text); letter-spacing: -.01em;
    }
    .gb-meta {
        margin-left: auto; color: var(--muted); font-size: .72rem;
        font-variant-numeric: tabular-nums; white-space: nowrap;
    }
    @media (max-width: 640px) {
        .gb-title { font-size: 1rem; }
        .gb-meta { display: none; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── ⚡ Infinite ticker tape — the terminal's heartbeat, top of view ──
    items = []
    feed_alive = False
    for label, tk in PULSE_TICKERS.items():
        q = fetch_portal_quote(tk)
        if q is None:
            items.append(f'<span class="tp-item"><span class="tp-sym">{label}</span>'
                         f'<span class="tp-dead">—</span></span><span class="tp-sep">⚡</span>')
            continue
        feed_alive = True
        px, diff, pct = q
        cls = "up" if diff >= 0 else "down"
        sign = "+" if diff >= 0 else ""
        items.append(
            f'<span class="tp-item"><span class="tp-sym">{label}</span>'
            f'<span class="tp-px">${px:,.2f}</span>'
            f'<span class="tp-pct {cls}">{sign}{pct:.2f}%</span></span>'
            f'<span class="tp-sep">⚡</span>'
        )
    seq = "".join(items)
    st.markdown(f'<div class="tape-wrap"><div class="tape">{seq}{seq}</div></div>',
                unsafe_allow_html=True)

    # ── Slim identity line (text-only — all cosmetic assets scrapped) ──
    st.markdown(
        f'<div class="gb-head"><span class="gb-title">NYARKO&#39;S TRADE MANAGER</span>'
        f'<span class="gb-meta">{datetime.now().strftime("%b %d, %I:%M %p")}</span></div>',
        unsafe_allow_html=True
    )

    if client is None:
        st.error("⚠️ ANTHROPIC_API_KEY not found — AI features are disabled.")

    macro_events = fetch_macro_calendar()

    left, right = st.columns([2, 1], gap="small")

    with left:
        # ── Marquee: the single nearest high-impact event ──
        next_up = next((e for e in macro_events if e.get("Status") == "⏳ Upcoming"), None)
        if next_up:
            st.markdown(
                f"""
                <div class="marquee">
                    <div class="mq-label">NEXT HIGH-IMPACT RELEASE</div>
                    <div class="mq-event">{html.escape(next_up['Currency'])} · {html.escape(next_up['Event'])}</div>
                    <div class="mq-meta">{html.escape(next_up['Time (ET)'])} ET · Forecast {html.escape(str(next_up['Forecast']))} · Previous {html.escape(str(next_up['Previous']))}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="marquee"><div class="mq-label">MACRO HORIZON</div>'
                '<div class="mq-event">No upcoming high-impact releases on the feed</div>'
                '<div class="mq-meta">Quiet week or feed refreshing — retries hourly</div></div>',
                unsafe_allow_html=True
            )

        st.subheader("Select Asset Pipeline to Initialize Deep Scan Workspace")
        names = list(wl.keys())
        for row_start in range(0, len(names), 3):
            row_names = names[row_start:row_start + 3]
            cols = st.columns(3)
            for col, asset_name in zip(cols, row_names):
                details = wl[asset_name]
                quote = fetch_portal_quote(details["ticker"])
                with col:
                    if quote is None:
                        st.markdown(
                            f"""<div class="asset-card feed-down">
                                <div class="ac-name">{asset_name}</div>
                                <div class="ac-err">— FEED DOWN —</div>
                                <div class="ac-sub">Quote source unavailable</div></div>""",
                            unsafe_allow_html=True
                        )
                    else:
                        c_price, diff, pct = quote
                        pct_class = "up" if diff >= 0 else "down"
                        sign = "+" if diff >= 0 else ""
                        try:
                            bias_label = compute_bias(load_market_data(details["ticker"]))["state"]
                        except Exception:
                            bias_label = "⚪ DATA ERROR"
                        st.markdown(
                            f"""<div class="asset-card">
                                <div class="ac-name">{asset_name}</div>
                                <div class="ac-price">${c_price:,.2f}{details.get('unit','')}</div>
                                <div class="ac-pct {pct_class}">{sign}{pct:.2f}% today</div>
                                <div class="ac-bias">{bias_label}</div></div>""",
                            unsafe_allow_html=True
                        )
                    if st.button(f"Initialize {asset_name} ▸", key=f"init_{asset_name}",
                                 use_container_width=True):
                        st.session_state.active_asset = asset_name
                        st.switch_page(PAGES["bias"])

        # ── Row 2: market trackers — initialize to add to watchlist + deep scan.
        #    Once initialized, an asset graduates into the pipeline rows above,
        #    so this row only shows instruments not yet activated. ──
        pending = [l for l in ["SPCX", "QQQ", "TLT"] if l not in wl]
        if pending:
            tcols = st.columns(3)
            for col, label in zip(tcols, pending):
                tk, role = MARKET_TRACKERS[label]
                q = fetch_portal_quote(tk)
                with col:
                    if q is None:
                        st.markdown(
                            f"""<div class="asset-card feed-down">
                                <div class="ac-name">{label}</div>
                                <div class="ac-err">— FEED DOWN —</div>
                                <div class="ac-sub">{html.escape(role)}</div></div>""",
                            unsafe_allow_html=True
                        )
                    else:
                        px, diff, pct = q
                        pct_class = "up" if diff >= 0 else "down"
                        sign = "+" if diff >= 0 else ""
                        st.markdown(
                            f"""<div class="asset-card">
                                <div class="ac-name">{label}</div>
                                <div class="ac-price">${px:,.2f}</div>
                                <div class="ac-pct {pct_class}">{sign}{pct:.2f}% today</div>
                                <div class="ac-bias">{html.escape(role)}</div></div>""",
                            unsafe_allow_html=True
                        )
                    if st.button(f"Initialize {label} ▸", key=f"init_trk_{label}",
                                 use_container_width=True):
                        if label not in st.session_state.watchlist:
                            st.session_state.watchlist[label] = {
                                "ticker": tk, "name": role, "unit": ""
                            }
                            save_watchlist_to_disk(st.session_state.watchlist)
                        st.session_state.active_asset = label
                        st.switch_page(PAGES["bias"])

    with right:
        with st.container(key="panel_health"):
            st.markdown('<div class="volt-title">⚡ SYSTEM HEALTH & BOT LINK</div>', unsafe_allow_html=True)
            feed_cls = "ok" if feed_alive else "err"
            st.markdown(f'<div class="health-row"><span class="dot {feed_cls}"></span> Market Data Feed'
                        f'<span class="health-sub">{"live" if feed_alive else "unreachable"}</span></div>',
                        unsafe_allow_html=True)
            ai_cls = "ok" if client is not None else "err"
            st.markdown(f'<div class="health-row"><span class="dot {ai_cls}"></span> AI Engine'
                        f'<span class="health-sub">{"key loaded" if client else "no API key"}</span></div>',
                        unsafe_allow_html=True)
            bot_cls, bot_sub = read_bot_status()
            st.markdown(f'<div class="health-row"><span class="dot {bot_cls}"></span> Telegram Alert Bot'
                        f'<span class="health-sub">{html.escape(bot_sub)}</span></div>',
                        unsafe_allow_html=True)

        st.subheader("🚨 Macro Week")
        with st.container(height=330, key="panel_macro"):
            if macro_events:
                render_macro_events(macro_events)
            else:
                st.warning("Macro feed returned nothing — quiet week or feed down.")


# =====================================================================
# PAGE 2: 🎯 BIAS ENGINE — 2:1:1 grid + Quick Prompts (Gateway pass)
# =====================================================================
def page_bias_engine():
    wl = get_watchlist()
    asset, title_col = asset_picker()
    details = wl[asset]
    with title_col:
        st.title(f"🎯 Bias Engine — {details.get('name', asset)}")
        st.markdown('<div class="volt-title">⚡ STATIC SHOCK INTELLIGENCE ENGINE CORE</div>',
                    unsafe_allow_html=True)

    with st.spinner("Computing statistical state..."):
        try:
            df = load_market_data(details["ticker"])
            bias = compute_bias(df)
            trades, stats = run_backtest(details["ticker"], asset)
        except Exception:
            st.error("Data feed failure for this asset. Try again shortly — Yahoo rate limits are usually temporary.")
            return

    banner = {"green": st.success, "red": st.error, "orange": st.warning, "gray": st.info}[bias["color"]]
    banner(f"**{bias['state']}** — {bias['headline']}")

    macro_events = fetch_macro_calendar()
    dir_stats = stats.get(bias["direction"] or "all", stats["all"])
    unit = details.get("unit", "")

    bias_snapshot = (
        f"- State: {bias['state']}\n"
        f"- Spot: ${bias['price']:,.2f} | Z-score: {bias['z']:+.2f} std devs\n"
        f"- 20 EMA: ${bias['baseline']:,.2f} | 200 EMA: ${bias['macro']:,.2f} ({bias['trend']})\n"
        f"- Bands: ${bias['lower']:,.2f} / ${bias['upper']:,.2f}\n"
        f"- Arm: ${bias['arm_level']:,.2f} | Invalidation: ${bias['invalidation']:,.2f} | Target: ${bias['target']:,.2f}"
    )
    stats_snapshot = (
        f"- Direction-relevant trades: {dir_stats['n']} | Win rate: {dir_stats['win_rate']*100:.1f}%\n"
        f"- Avg win: {dir_stats['avg_win']*100:+.2f}% | Avg loss: {dir_stats['avg_loss']*100:+.2f}%\n"
        f"- Strategy compounded: {stats['strategy_return']*100:+.2f}% vs B&H {stats['buy_hold_return']*100:+.2f}%\n"
        f"- Max drawdown (trade-level): {stats['max_drawdown']*100:.2f}%"
    )

    g1, g2, g3 = st.columns([2, 1, 1], gap="small")

    with g1:
        with st.container(key="panel_evidence"):
            st.markdown('<div class="volt-title">⚡ EVIDENCE CORE</div>', unsafe_allow_html=True)
            r1 = st.columns(2)
            r1[0].metric("Spot Price", f"${bias['price']:,.2f}{unit}")
            r1[1].metric("Z-Score", f"{bias['z']:+.2f}σ",
                         help="Standard deviations from the 20 EMA equilibrium. ±2σ = band touch.")
            r2 = st.columns(2)
            r2[0].metric("20 EMA Equilibrium", f"${bias['baseline']:,.2f}")
            r2[1].metric("HTF Trend (200 EMA)", bias["trend"].split(" ")[0], help=bias["trend"])
            r3 = st.columns(2)
            r3[0].metric("Lower Band (−2σ)", f"${bias['lower']:,.2f}")
            r3[1].metric("Upper Band (+2σ)", f"${bias['upper']:,.2f}")

    with g2:
        with st.container(key="panel_actions"):
            st.markdown('<div class="volt-title">⚡ EXECUTION LEVELS</div>', unsafe_allow_html=True)
            st.metric("Arm Level", f"${bias['arm_level']:,.2f}",
                      f"{bias['dist_to_arm_pct']:+.2f}% away", delta_color="off")
            st.metric("Invalidation", f"${bias['invalidation']:,.2f}",
                      help=f"Beyond this level violates the {STOP_LOSS_PCT*100:.1f}% risk budget the backtest assumes.")
            st.metric("Target (20 EMA)", f"${bias['target']:,.2f}",
                      f"{bias['dist_to_target_pct']:+.2f}% from spot", delta_color="off")

    with g3:
        with st.container(key="panel_setup"):
            st.markdown('<div class="volt-title">⚡ SETUP BASE RATES (5Y)</div>', unsafe_allow_html=True)
            st.metric("Win Rate", f"{dir_stats['win_rate']*100:.1f}%",
                      help=f"Based on {dir_stats['n']} historical trades of this direction.")
            st.metric("Avg Win / Loss",
                      f"{dir_stats['avg_win']*100:+.1f}% / {dir_stats['avg_loss']*100:+.1f}%")

    # ── ⚡ Macro week: fixed horizontal track — structurally locked,
    #    never displaces the modules below it ──
    if macro_events:
        st.markdown('<div class="volt-title">⚡ MACRO WEEK TRACK</div>', unsafe_allow_html=True)
        render_macro_track(macro_events)

    # ── Quick Prompts + AI memo row ──
    q1, q2, q3 = st.columns([3, 1, 2], vertical_alignment="bottom", gap="small")
    with q1:
        question = st.selectbox("Quick Prompts", QUICK_PROMPTS, key=f"qp_{asset}",
                                label_visibility="collapsed")
    with q2:
        ask = st.button("Ask ⚡", use_container_width=True, key=f"qp_btn_{asset}")
    with q3:
        memo_click = st.button("🤖 Generate Full AI Bias Memo",
                               use_container_width=True, key=f"memo_btn_{asset}")

    context = bias_snapshot + "\n" + stats_snapshot

    if ask and require_client("quick prompts"):
        with st.spinner("Answering from the live readout..."):
            try:
                st.session_state[f"qp_ans_{asset}"] = (
                    question, ai_quick_answer(client, question, details.get("name", asset),
                                              details["ticker"], context))
            except Exception:
                st.error("AI call failed — check your API key, network, or rate limits.")

    qp = st.session_state.get(f"qp_ans_{asset}")
    if qp:
        st.info(f"**{qp[0]}**\n\n{md_safe(qp[1])}")
        if st.button("📤 Send to Telegram", key=f"qp_tg_{asset}"):
            ok = send_telegram_out(f"🎯 {details.get('name', asset)} — {qp[0]}\n\n{qp[1]}")
            if ok is True:
                st.success("Dispatched to your Telegram.")
            elif ok is False:
                st.error("Telegram API rejected the send — check the bot token / chat id.")
            else:
                st.info("Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your .env (local) or Streamlit Secrets (cloud) to enable dispatch.")

    if memo_click and require_client("the AI bias memo"):
        macro_snapshot = "\n".join(
            f"- {e['Currency']}: {e['Event']} (Forecast: {e['Forecast']})" for e in macro_events
        ) or "- None detected"
        with st.spinner("Interpreting the numbers..."):
            try:
                st.session_state[f"memo_{asset}"] = ai_bias_memo(
                    client, details.get("name", asset), details["ticker"],
                    bias_snapshot, stats_snapshot, macro_snapshot)
            except Exception:
                st.error("AI call failed — check your API key, network, or rate limits.")

    memo = st.session_state.get(f"memo_{asset}")
    if memo:
        st.markdown(md_safe(memo))
        if st.button("📤 Send memo to Telegram", key=f"memo_tg_{asset}"):
            ok = send_telegram_out(f"🧠 Bias Memo — {details.get('name', asset)}\n\n{memo}")
            if ok is True:
                st.success("Dispatched to your Telegram.")
            elif ok is False:
                st.error("Telegram API rejected the send — check the bot token / chat id.")
            else:
                st.info("Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your .env (local) or Streamlit Secrets (cloud) to enable dispatch.")


# =====================================================================
# PAGE 3: 📈 LIVE CHART — viewport-budgeted height (Pass B)
# =====================================================================
def page_live_chart():
    wl = get_watchlist()
    asset, title_col = asset_picker()
    details = wl[asset]
    with title_col:
        st.title(f"📈 Live Chart — {details.get('name', asset)}")

    with st.expander("📖 How to read this chart"):
        st.markdown("""
        - **20 EMA (Baseline)** = institutional equilibrium / fair value anchor.
        - **±2σ Bands** = Premium and Discount Arrays. A close beyond a band is a statistical overextension.
        - **200 EMA (Macro Trend)** = higher-timeframe bias filter. The strategy only trades reversion *with* this trend.
        """)

    # Viewport budget: ~900px effective height on a 13" Air minus browser
    # chrome (~120), fixed rail (~48), title row (~52), expander (~44),
    # caption (~30), paddings (~60) → ~640px of chart.
    CHART_H = 620

    @st.fragment(run_every=15)
    def render_live_chart():
        try:
            live_df = load_market_data(details["ticker"])
        except Exception:
            st.error("Chart data feed failure — retrying automatically.")
            return
        valid_plot = live_df.tail(500).dropna().copy()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Price"], mode='lines', name=f'{asset} Price', line=dict(color='#E8B54A', width=2.5)))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Baseline"], mode='lines', name='20 EMA Baseline', line=dict(color='#37B7C3', width=1.5, dash='dash')))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Macro_Filter"], mode='lines', name='200 EMA Macro Trend', line=dict(color='#97A1B3', width=2)))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Upper_Band"], mode='lines', name='Upper Band (Premium)', line=dict(color='#E4574C', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=valid_plot.index, y=valid_plot["Lower_Band"], mode='lines', name='Lower Band (Discount)', line=dict(color='#2FBF71', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.01)'))

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(16,20,31,.6)",
            margin=dict(l=20, r=20, t=16, b=16), height=CHART_H, hovermode="x unified",
            font=dict(family="Space Grotesk, sans-serif"),
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickprefix="$", tickformat=",.2f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{asset}_{datetime.now().timestamp()}")
        st.caption("Auto-refreshes every 15 seconds.")

    render_live_chart()


# =====================================================================
# PAGE 4: 📰 NEWS & SENTIMENT — 1:2 grid, internal-scroll gallery (Pass B)
# =====================================================================
def page_sentiment():
    wl = get_watchlist()
    asset, title_col = asset_picker()
    details = wl[asset]
    with title_col:
        st.title(f"📰 News & Sentiment — {details.get('name', asset)}")

    with st.spinner("Scanning market news..."):
        items = fetch_news_items(details["ticker"])

    if not items:
        st.warning("No headlines available from the feed right now.")
        return

    akey = f"news_ai_{details['ticker']}"
    left, right = st.columns([1, 2], gap="small")

    with left:
        with st.container(key="panel_sent_overview"):
            st.markdown('<div class="volt-title">⚡ SENTIMENT ENGINE CORE</div>', unsafe_allow_html=True)
            if st.button("🤖 Analyze Sentiment & Macro Impact", use_container_width=True):
                if require_client("sentiment analysis"):
                    with st.spinner("Reading the tape..."):
                        try:
                            headline_block = "\n".join(f"{i}. {it['title']}" for i, it in enumerate(items))
                            st.session_state[akey] = ai_news_analysis(
                                client, details.get("name", asset), details["ticker"], headline_block)
                        except Exception:
                            st.error("AI call failed — check your API key, network, or rate limits.")

            analysis = st.session_state.get(akey)
            if analysis and analysis.get("overall"):
                o = analysis["overall"]
                st.metric("Overall Sentiment", str(o.get("sentiment", "?")),
                          f"score {o.get('score', '?')} / 10", delta_color="off")
                st.info(md_safe(str(o.get("summary", ""))))
                ok_btn = st.button("📤 Send readout to Telegram", use_container_width=True,
                                   key=f"sent_tg_{asset}")
                if ok_btn:
                    ok = send_telegram_out(
                        f"📰 {details.get('name', asset)} sentiment: {o.get('sentiment','?')} "
                        f"({o.get('score','?')}/10)\n\n{o.get('summary','')}")
                    if ok is True:
                        st.success("Dispatched.")
                    elif ok is False:
                        st.error("Telegram rejected the send — check bot token / chat id.")
                    else:
                        st.info("Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env or Streamlit Secrets to enable dispatch.")
            elif analysis and analysis.get("raw"):
                st.markdown(md_safe(analysis["raw"]))
            else:
                st.caption("Run the analysis to score the tape and populate every card's Macro read.")

    analysis = st.session_state.get(akey)
    impacts = {}
    if analysis and analysis.get("overall"):
        impacts = {imp.get("i"): imp for imp in analysis.get("impacts", [])}

    with right:
        with st.container(height=560, key="panel_news"):
            for row_start in range(0, len(items), 2):
                cols = st.columns(2)
                for offset, col in enumerate(cols):
                    idx = row_start + offset
                    if idx >= len(items):
                        continue
                    it = items[idx]
                    with col:
                        safe_title = html.escape(it["title"])
                        link = html.escape(it.get("link", ""), quote=True)
                        title_html = (f'<a href="{link}" target="_blank">{safe_title}</a>'
                                      if link else safe_title)
                        st.markdown(
                            f"""
                            <div class="news-card">
                                <div class="nc-title">{title_html}</div>
                                <div class="nc-meta">{html.escape(it.get('published', '') or 'Yahoo Finance RSS')}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        with st.expander("🔍 Macro read"):
                            imp = impacts.get(idx)
                            if imp:
                                tilt = str(imp.get("tilt", "neutral")).lower()
                                if tilt not in ("bullish", "bearish", "neutral"):
                                    tilt = "neutral"
                                st.markdown(
                                    f'<span class="tilt {tilt}">{tilt.upper()}</span>&nbsp; '
                                    f'{html.escape(str(imp.get("impact", "")))}',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.caption("Run the analysis to populate this card.")


# =====================================================================
# PAGE 5: 📊 STRATEGY BACKTEST MATRIX — 3-column architecture
# =====================================================================
def page_backtest():
    wl = get_watchlist()
    asset, title_col = asset_picker()
    details = wl[asset]
    with title_col:
        st.title(f"📊 Backtest Matrix — {details.get('name', asset)}")
        st.markdown('<div class="volt-title">⚡ STATIC SHOCK INTELLIGENCE ENGINE CORE</div>',
                    unsafe_allow_html=True)

    with st.spinner("Running 5-year backtests across all strategies..."):
        try:
            results = {k: run_backtest(details["ticker"], asset, k) for k in STRATEGIES}
        except Exception:
            st.error("Data feed failure for this asset — try again shortly.")
            return

    keys = list(STRATEGIES.keys())
    selected = st.radio("Strategy", keys,
                        format_func=lambda k: STRATEGIES[k]["name"],
                        horizontal=True, label_visibility="collapsed")

    trades, stats = results[selected]
    label, cls, pf, exp = viability(stats)
    pf_txt = "∞" if pf == float("inf") else f"{pf:.2f}"
    banner = {"good": st.success, "mid": st.warning, "bad": st.error}[cls]
    banner(f"**STRATEGY VIABILITY: {label}** — {STRATEGIES[selected]['desc']}. "
           f"Profit factor **{pf_txt}**, expectancy **{exp*100:+.2f}% per trade** across {stats['all']['n']} trades.")

    c1, c2, c3 = st.columns([1, 1, 1.35], gap="small")

    with c1:
        with st.container(key="panel_perf"):
            st.markdown('<div class="volt-title">⚡ PERFORMANCE CORE</div>', unsafe_allow_html=True)
            r1 = st.columns(2)
            r1[0].metric("Strategy Return", f"{stats['strategy_return']*100:+.2f}%")
            r1[1].metric("Buy & Hold", f"{stats['buy_hold_return']*100:+.2f}%")
            st.metric("Max Drawdown", f"{stats['max_drawdown']*100:.2f}%",
                      help="Trade-close equity — open-position drawdown can be worse.")
            st.markdown('<div class="volt-title">⚡ BASE RATES</div>', unsafe_allow_html=True)
            for key, label2 in [("all", "All"), ("long", "Longs"), ("short", "Shorts")]:
                s = stats[key]
                st.markdown(
                    f'<div class="health-row">{label2}'
                    f'<span class="health-sub">{s["n"]} trades · win {s["win_rate"]*100:.1f}% · '
                    f'avg {s["avg_win"]*100:+.1f}% / {s["avg_loss"]*100:+.1f}%</span></div>',
                    unsafe_allow_html=True
                )

    with c2:
        with st.container(key="panel_matrix"):
            st.markdown('<div class="volt-title">⚡ STRATEGY MATRIX</div>', unsafe_allow_html=True)
            for k in keys:
                _, stats_k = results[k]
                label_k, cls_k, pf_k, _ = viability(stats_k)
                pft = "∞" if pf_k == float("inf") else f"{pf_k:.2f}"
                wr_k = stats_k["all"]["win_rate"] * 100
                ret_k = stats_k["strategy_return"] * 100
                n_k = stats_k["all"]["n"]
                sel = " selected" if k == selected else ""
                st.markdown(
                    f"""
                    <div class="strat-card{sel}">
                        <div class="sc-name">{STRATEGIES[k]["name"]}</div>
                        <div class="sc-verdict {cls_k}">{label_k}</div>
                        <div class="sc-line">PF {pft} · Win {wr_k:.0f}%</div>
                        <div class="sc-line">{ret_k:+.1f}% · {n_k} trades</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.caption("Toggle with the selector above — all strategies run the same honest execution model.")

    with c3:
        st.markdown('<div class="volt-title">⚡ TRANSACTION HISTORY</div>', unsafe_allow_html=True)
        with st.container(height=440, key="panel_tradelog"):
            render_trade_log(trades, limit=40)


# =====================================================================
# PAGE 6: 🦅 OPTIONS CO-PILOT (optional — never a gate to analysis)
# =====================================================================
def page_copilot():
    wl = get_watchlist()
    asset, title_col = asset_picker()
    details = wl[asset]
    with title_col:
        st.title(f"🦅 Options Co-Pilot — {details.get('name', asset)}")
    st.caption("Optional: log a live options position to have it stress-tested against the statistics. All analysis pages work without this.")

    if asset not in st.session_state.active_trades:
        st.session_state.active_trades[asset] = None

    current_trade = st.session_state.active_trades[asset]

    if current_trade is None:
        st.subheader("📝 Log an Active Options Position")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            type_opt = st.selectbox("Position Type", ["Long Call 🟢", "Long Put 🔴"], key=f"type_{asset}")
        with c2:
            strike = st.number_input("Strike Price ($)", min_value=0.0, step=0.5, key=f"strike_{asset}")
        with c3:
            exp_date = st.date_input("Expiration Date", key=f"exp_{asset}")
        with c4:
            premium = st.number_input("Entry Premium / Cost ($)", min_value=0.0, step=0.01, key=f"prem_{asset}")

        thesis = st.text_area("Trade thesis (e.g., Playing the discount bounce off the Lower Band)",
                          key=f"thesis_{asset}", height=70)

        if st.button("🚀 Deploy Co-Pilot Tracking", use_container_width=True):
            st.session_state.active_trades[asset] = {
                "Type": type_opt,
                "Strike": strike,
                "Expiration": exp_date.strftime("%Y-%m-%d"),
                "Entry Premium": premium,
                "Thesis": thesis,
                "Logged At": datetime.now().strftime("%Y-%m-%d %I:%M %p")
            }
            st.rerun()
        return

    st.warning(f"🚨 ACTIVE POSITION: {current_trade['Type']} | Strike: ${current_trade['Strike']} | Exp: {current_trade['Expiration']}")
    try:
        days_left = (datetime.strptime(current_trade['Expiration'], "%Y-%m-%d").date() - datetime.today().date()).days
    except Exception:
        days_left = "N/A"

    tc1, tc2 = st.columns([3, 1])
    with tc1:
        st.markdown(f"**Your Thesis:** *{current_trade['Thesis']}*")
        st.caption(f"Logged: {current_trade['Logged At']}")
    with tc2:
        if st.button("🏁 Clear Position", use_container_width=True):
            st.session_state.active_trades[asset] = None
            st.rerun()

    st.markdown("---")
    if st.button("🦅 Run AI Stress-Test", use_container_width=True):
        if require_client("the AI stress-test"):
            try:
                df = load_market_data(details["ticker"])
                bias = compute_bias(df)
                trades, stats = run_backtest(details["ticker"], asset)
            except Exception:
                st.error("Data feed failure — cannot stress-test without live statistics.")
                return

            market_snapshot = (
                f"- Spot: ${bias['price']:,.2f} | Z-score: {bias['z']:+.2f} std devs\n"
                f"- 20 EMA: ${bias['baseline']:,.2f} | 200 EMA: ${bias['macro']:,.2f} ({bias['trend']})\n"
                f"- Bands: ${bias['lower']:,.2f} / ${bias['upper']:,.2f}"
            )
            s = stats["all"]
            stats_snapshot = (
                f"- Trades: {s['n']} | Win rate: {s['win_rate']*100:.1f}%\n"
                f"- Avg win: {s['avg_win']*100:+.2f}% | Avg loss: {s['avg_loss']*100:+.2f}%\n"
                f"- Max drawdown: {stats['max_drawdown']*100:.2f}%"
            )
            trade_key = f"{current_trade['Type']}|{current_trade['Strike']}|{current_trade['Expiration']}|{current_trade['Entry Premium']}|{current_trade['Logged At']}"
            with st.spinner("🦅 Cross-examining your thesis..."):
                try:
                    analysis = ai_stress_test(client, asset, trade_key, days_left,
                                              round(bias["price"], 0), market_snapshot, stats_snapshot)
                    st.chat_message("assistant", avatar="🦅").markdown(md_safe(analysis))
                except Exception:
                    st.error("AI call failed — check your API key, network, or rate limits.")


# =====================================================================
# PAGE 7: ⚙️ WATCHLIST MANAGER
# =====================================================================
def page_watchlist():
    wl = get_watchlist()
    st.title("⚙️ Watchlist Manager")
    st.caption("This watchlist drives every page AND the Telegram alert bot (both read watchlist.json).")

    st.subheader("Current Watchlist")
    for asset_name in list(wl.keys()):
        details = wl[asset_name]
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.markdown(f"**{asset_name}** — {details.get('name', asset_name)}")
        c2.code(details["ticker"], language=None)
        if len(wl) > 1:
            if c3.button("🗑️ Remove", key=f"rm_{asset_name}", use_container_width=True):
                del st.session_state.watchlist[asset_name]
                save_watchlist_to_disk(st.session_state.watchlist)
                st.rerun()
        else:
            c3.caption("Last asset")

    st.markdown("---")
    st.subheader("➕ Add an Asset")
    a1, a2, a3, a4 = st.columns([2, 2, 1, 1.2], vertical_alignment="bottom")
    with a1:
        new_label = st.text_input("Display name", placeholder="e.g., Tesla")
    with a2:
        new_ticker = st.text_input("Yahoo Finance ticker", placeholder="e.g., TSLA, GC=F, BTC-USD")
    with a3:
        new_unit = st.text_input("Unit suffix", placeholder="/sh", value="/sh")
    with a4:
        add_clicked = st.button("Validate & Add", use_container_width=True)

    if add_clicked:
        label = new_label.strip()
        ticker = new_ticker.strip().upper()
        if not label or not ticker:
            st.error("Both a display name and a ticker are required.")
        elif label in wl:
            st.error(f"'{label}' is already on the watchlist.")
        elif any(d["ticker"] == ticker for d in wl.values()):
            st.error(f"Ticker {ticker} is already tracked under another name.")
        else:
            with st.spinner(f"Validating {ticker} against the data feed..."):
                quote = fetch_portal_quote(ticker)
            if quote is None:
                st.error(f"❌ {ticker} returned no data from Yahoo Finance. Check the symbol (futures need the =F suffix, indices need ^, crypto needs -USD).")
            else:
                st.session_state.watchlist[label] = {
                    "ticker": ticker,
                    "name": label,
                    "unit": new_unit.strip()
                }
                saved = save_watchlist_to_disk(st.session_state.watchlist)
                st.success(f"✅ {label} ({ticker}) added — last price ${quote[0]:,.2f}.")
                if not saved:
                    st.warning("Could not write watchlist.json to disk — the addition is active for this session only.")
                st.rerun()

    st.markdown("---")
    st.info(
        "**Persistence note:** additions save to watchlist.json. Locally that's permanent. "
        "On Streamlit Cloud, the filesystem resets on every reboot/redeploy — to make an asset "
        "permanent there (and visible to the alert bot), edit watchlist.json directly in your "
        "GitHub repo (web editor, 30 seconds, no code)."
    )


# =====================================================================
# 🧭 NAVIGATION — dual gold rails (top: desktop · bottom dock: mobile)
# =====================================================================
PAGES = {}

pages = [
    st.Page(page_command_center, title="Briefing", icon="🎛️", default=True),
    st.Page(page_bias_engine, title="Bias", icon="🎯"),
    st.Page(page_live_chart, title="Chart", icon="📈"),
    st.Page(page_sentiment, title="News", icon="📰"),
    st.Page(page_backtest, title="Backtest", icon="📊"),
    st.Page(page_copilot, title="Co-Pilot", icon="🦅"),
    st.Page(page_watchlist, title="Watchlist", icon="⚙️"),
]

PAGES["briefing"] = pages[0]
PAGES["bias"] = pages[1]

nav = st.navigation(pages, position="sidebar")   # NATIVE desktop navigation


def render_mobile_dock():
    """Fixed bottom thumb dock — visible ≤768px only (CSS-gated)."""
    with st.container(key="bottomnav"):
        for p in pages:
            st.page_link(p)


render_mobile_dock()

nav.run()
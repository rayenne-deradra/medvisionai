"""Visual identity: MedVisionAI navy and gold, as a modern dashboard (every page, brain MRI included).

Navy sidebar, cool off-white canvas, white rounded cards with soft shadows, a gradient hero banner, one modern
sans-serif (Plus Jakarta Sans) with JetBrains Mono for small labels and numbers.
"""
from __future__ import annotations

import html
from functools import lru_cache

from ..config import ASSETS_DIR

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,500;1,9..144,600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --mv-bg: #F4F6FB; --mv-card: #FFFFFF; --mv-line: #E5E8F1; --mv-line-2: #D6DBEA;
  --mv-ink: #131837; --mv-ink-2: #4A5072; --mv-muted: #858AA6;
  --mv-navy: #1B2246; --mv-navy-2: #2A3375; --mv-indigo: #4C5BD4;
  --mv-gold: #C9A86A; --mv-gold-2: #F0DDB0; --mv-gold-ink: #9C7432;
  --mv-rose: #D14B5A; --mv-rose-bg: #FDEEF0; --mv-teal: #17917A; --mv-teal-bg: #E7F6F2; --mv-amber: #B7791F;
  --mv-radius: 20px;
  --mv-shadow: 0 1px 2px rgba(19,24,55,.04), 0 8px 24px rgba(19,24,55,.06);
}
html, body, .stApp, [data-testid="stMarkdownContainer"], button, input, textarea, select, label {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
}
.stApp { background: var(--mv-bg); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1120px; padding-top: 1.6rem; padding-bottom: 7rem; }
h1, h2, h3 { font-family: 'Plus Jakarta Sans', sans-serif !important; font-weight: 800 !important;
  letter-spacing: -.02em; color: var(--mv-ink); }
[data-testid="stImage"] img { border-radius: 14px; }

/* ---------------------------------------------------------------- sidebar */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1B2246 0%, #161C3C 100%); border-right: none; }
[data-testid="stSidebarNav"] a { border-radius: 12px; margin: 2px 0; }
.st-key-mv_nav { padding-bottom: 12px; margin-bottom: 6px; border-bottom: 1px solid #2E3768; gap: 2px; }
.st-key-mv_nav a { border-radius: 12px; padding: 6px 10px; }
.st-key-mv_nav a:hover { background: rgba(255,255,255,.06); }
.st-key-mv_nav a[aria-current="page"], .st-key-mv_nav a[data-active="true"] { background: rgba(201,168,106,.16); }
.st-key-mv_nav a[aria-current="page"] span, .st-key-mv_nav a[data-active="true"] span { color: var(--mv-gold-2) !important; font-weight: 600; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(201,168,106,.16); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: var(--mv-gold-2) !important; font-weight: 600; }
[data-testid="stSidebar"] .stButton > button { justify-content: flex-start; text-align: left; border-radius: 12px; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] { color: var(--mv-navy); font-weight: 700;
  background: linear-gradient(135deg, #D8BC85, #C9A86A); border: none; }
[data-testid="stSidebar"] [data-testid="stExpander"] details { border-color: #2E3768; border-radius: 14px;
  background: rgba(255,255,255,.03); }
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
[data-testid="stSidebar"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
[data-testid="stSidebar"] [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; }
[data-testid="stSidebar"] [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; }
[data-testid="stSidebar"] .mv-label { color: #8D93B5; }
[data-testid="stSidebar"] .mv-disclaimer { border-color: rgba(201,168,106,.28); background: rgba(201,168,106,.07);
  color: #D9CCAE; }
[data-testid="stSidebar"] .mv-disclaimer b { color: var(--mv-gold); }

/* ---------------------------------------------------------------- generic pieces */
.mv-label { font-family: 'JetBrains Mono', monospace; font-size: .68rem; font-weight: 500; letter-spacing: .14em;
  text-transform: uppercase; color: var(--mv-muted); margin: 4px 0 10px; }
.mv-h { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: 26px 0 12px; }
.mv-h h3 { font-size: 1.15rem !important; margin: 0 !important; padding: 0 !important; }
.mv-h span { color: var(--mv-muted); font-size: .85rem; }
.mv-disclaimer { border: 1px solid #EBDDBD; background: #FFF9EC; color: #6B5527; border-radius: 14px;
  padding: 10px 14px; font-size: .82rem; line-height: 1.5; }
.mv-disclaimer b { color: var(--mv-gold-ink); }

/* keyed containers become cards (st.container(key="mv_images") -> class st-key-mv_images) */
.st-key-mv_images, .st-key-mv_probs, .st-key-mv_reasons { background: var(--mv-card); border: 1px solid var(--mv-line);
  border-radius: var(--mv-radius); box-shadow: var(--mv-shadow); padding: 20px 22px; }
/* Streamlit pulls the last text block 1rem down; cancel it so text sits evenly inside the card */
:is(.st-key-mv_images, .st-key-mv_probs, .st-key-mv_reasons) [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
:is(.st-key-mv_images, .st-key-mv_probs, .st-key-mv_reasons) [data-testid="stMarkdown"] { margin-bottom: 0 !important; }
:is(.st-key-mv_images, .st-key-mv_probs, .st-key-mv_reasons) .mv-foot:last-child { margin-bottom: 0; }
.st-key-mv_reasons .mv-reasons { margin-bottom: 6px; }

/* buttons, inputs, expanders */
.stButton > button, .stDownloadButton > button { border-radius: 12px; font-weight: 600; transition: all .15s ease; }
[data-testid="stMain"] .stButton > button[kind="primary"], [data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--mv-navy-2), var(--mv-navy)); border: none;
  box-shadow: 0 6px 16px rgba(27,34,70,.22); }
[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover { transform: translateY(-1px); }
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] details { background: var(--mv-card);
  border: 1px solid var(--mv-line); border-radius: 16px; box-shadow: var(--mv-shadow); }
[data-testid="stFileUploaderDropzone"] { background: var(--mv-card); border: 1.5px dashed var(--mv-line-2);
  border-radius: var(--mv-radius); padding: 22px 20px; transition: border-color .15s ease, background .15s ease; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--mv-indigo); background: #FAFBFF; }
[data-testid="stAlert"] { border-radius: 14px; }

/* ---------------------------------------------------------------- masthead */
.mv-mast { display: flex; align-items: center; gap: 22px; padding: 10px 0 26px; margin: 0 0 8px;
  border-bottom: 1px solid var(--mv-line); }
.mv-mast img { width: 64px; height: 64px; flex: none; border-radius: 16px; box-shadow: 0 10px 24px rgba(27,34,70,.18); }
.mv-mast .brand { font-family: 'JetBrains Mono', monospace; font-size: .74rem; font-weight: 600; letter-spacing: .26em;
  text-transform: uppercase; color: var(--mv-gold-ink); }
.mv-mast .brand span { color: var(--mv-muted); font-weight: 500; }
.mv-mast .brand span::before { content: ""; display: inline-block; width: 22px; height: 1px; margin: 0 10px 3px;
  background: var(--mv-gold); vertical-align: middle; }
.mv-mast h1 { font-size: clamp(1.7rem, 3.6vw, 2.5rem) !important; line-height: 1.1 !important; margin: 6px 0 0 !important;
  padding: 0 !important; font-weight: 800 !important; }
.mv-mast h1 em { font-style: normal; color: var(--mv-gold-ink); }
.mv-mast h1 .stop { margin-left: -.1em; }
@media (max-width: 640px) {
  .mv-mast { gap: 14px; }
  .mv-mast img { width: 48px; height: 48px; border-radius: 12px; }
  .mv-mast .brand { font-size: .62rem; letter-spacing: .18em; }
  .mv-mast .brand span { display: block; margin-top: 2px; }
  .mv-mast .brand span::before { display: none; }
}

/* ---------------------------------------------------------------- result header */
.mv-result { background: var(--mv-card); border: 1px solid var(--mv-line); border-radius: var(--mv-radius);
  box-shadow: var(--mv-shadow); padding: 20px 22px; margin: 8px 0 16px; }
.mv-result-top { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.mv-finding { display: flex; align-items: center; gap: 14px; }
.mv-finding .ic { width: 48px; height: 48px; border-radius: 14px; display: grid; place-items: center; font-size: 1.4rem; font-weight: 800; }
.mv-finding .t { font-size: 1.45rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.mv-finding .s { color: var(--mv-muted); font-size: .85rem; margin-top: 2px; overflow-wrap: anywhere; }
.mv-finding > div:last-child { min-width: 0; }
.mv-finding.rose .ic { background: var(--mv-rose-bg); color: var(--mv-rose); } .mv-finding.rose .t { color: var(--mv-rose); }
.mv-finding.teal .ic { background: var(--mv-teal-bg); color: var(--mv-teal); } .mv-finding.teal .t { color: var(--mv-teal); }
.mv-finding.muted .ic { background: #EEF0F6; color: var(--mv-muted); } .mv-finding.muted .t { color: var(--mv-ink-2); }
.mv-chip { font-size: .76rem; font-weight: 700; padding: 6px 12px; border-radius: 999px; white-space: nowrap; }
.mv-chip.High { color: var(--mv-teal); background: var(--mv-teal-bg); }
.mv-chip.Moderate { color: var(--mv-amber); background: #FDF4E3; }
.mv-chip.Low, .mv-chip.Not { color: var(--mv-rose); background: var(--mv-rose-bg); }
.mv-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 18px; }
.mv-kpi { background: #F8F9FD; border: 1px solid var(--mv-line); border-radius: 16px; padding: 12px 14px; min-width: 0; }
.mv-kpi .k { font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .12em; text-transform: uppercase; color: var(--mv-muted); }
.mv-kpi .v { font-size: 1.12rem; font-weight: 700; color: var(--mv-ink); margin-top: 4px; overflow-wrap: anywhere; line-height: 1.25; }
.mv-kpi .v.big { font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; }
.mv-kpi .meter { height: 6px; border-radius: 6px; background: #E8EBF4; margin-top: 8px; overflow: hidden; }
.mv-kpi .meter span { display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #E88A94, var(--mv-rose)); }
@media (max-width: 820px) { .mv-kpis { grid-template-columns: repeat(2, 1fr); } }

/* ---------------------------------------------------------------- probabilities */
.mv-prob { display: grid; grid-template-columns: minmax(120px, 1.25fr) 1.6fr 58px; align-items: center; gap: 12px;
  padding: 6px 0; font-size: .86rem; color: var(--mv-ink-2); }
.mv-prob .track { height: 8px; background: #EEF0F6; border-radius: 8px; overflow: hidden; }
.mv-prob .fill { display: block; height: 100%; background: #B4BAD3; border-radius: 8px; }
.mv-prob.top .fill { background: linear-gradient(90deg, var(--mv-indigo), var(--mv-navy)); }
.mv-prob.top .n { color: var(--mv-ink); font-weight: 700; }
.mv-prob.tumor .fill { background: linear-gradient(90deg, #E88A94, var(--mv-rose)); }
.mv-prob.tumor .n { color: var(--mv-rose); font-weight: 700; }
.mv-prob .p { text-align: right; font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: var(--mv-ink); }
@media (max-width: 520px) { .mv-prob { grid-template-columns: 1fr 1fr 50px; font-size: .78rem; } }
.mv-reasons { list-style: none; margin: 4px 0 0; padding: 0; }
.mv-reasons li { position: relative; padding: 7px 0 7px 22px; color: var(--mv-ink-2); font-size: .86rem; line-height: 1.5;
  border-top: 1px solid var(--mv-line); }
.mv-reasons li:first-child { border-top: none; }
.mv-reasons li::before { content: ""; position: absolute; left: 4px; top: 14px; width: 7px; height: 7px; border-radius: 50%;
  background: var(--mv-gold); }
.mv-foot { margin-top: 10px; font-size: .74rem; color: var(--mv-muted); line-height: 1.5; }
.mv-legend { display: flex; align-items: center; gap: 8px; font-size: .7rem; color: var(--mv-muted); margin-top: 8px; }
.mv-legend span.g { flex: 1; height: 6px; border-radius: 4px; border: 1px solid var(--mv-line);
  background: linear-gradient(90deg, rgba(255,0,0,0) 10%, rgba(255,40,0,.55) 45%, #FFB000 80%, #FFF200); }

/* ---------------------------------------------------------------- examples gallery */
.st-key-mv_examples [data-testid="stImage"] img { aspect-ratio: 1 / 1; object-fit: cover; transition: transform .15s ease; }
.st-key-mv_examples [data-testid="stImage"] img:hover { transform: scale(1.03); }
.st-key-mv_examples .stButton > button { font-size: .76rem; font-weight: 600; padding: 2px 6px; min-height: 0; color: var(--mv-ink-2); }

/* ---------------------------------------------------------------- chat */
[data-testid="stChatMessage"] { background: var(--mv-card); border: 1px solid var(--mv-line); border-radius: 18px;
  padding: 14px 18px; box-shadow: var(--mv-shadow); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarCustom"]) { background: #EEF0FB; border-color: #DCE0F5; box-shadow: none; }
[data-testid="stChatInput"] { border-radius: 18px; box-shadow: var(--mv-shadow); }
[data-testid="stChatInput"] textarea { font-size: 1rem; }
[data-testid="stBottomBlockContainer"], [data-testid="stBottom"] > div { background: var(--mv-bg); }
.st-key-mv_suggest .stButton > button { border-radius: 999px; background: var(--mv-card); border: 1px solid var(--mv-line);
  color: var(--mv-ink-2); font-weight: 500; font-size: .86rem; box-shadow: var(--mv-shadow); text-align: left; }
.st-key-mv_suggest .stButton > button p { white-space: normal; text-align: left; line-height: 1.35; }
.st-key-mv_suggest .stButton > button { justify-content: flex-start; padding: 10px 16px; height: 100%; }
.st-key-mv_suggest .stButton > button:hover { border-color: var(--mv-indigo); color: var(--mv-indigo); }
.mv-chat-hero { text-align: center; margin: 4vh auto 18px; max-width: 640px; }
.mv-chat-hero img { width: 54px; height: 54px; margin-bottom: 12px; }
.mv-chat-hero h1 { font-size: clamp(1.6rem, 3.4vw, 2.2rem) !important; margin: 0 !important; padding: 0 !important; }
.mv-chat-hero p { color: var(--mv-ink-2); margin-top: 8px; }
.mv-scope { display: inline-flex; gap: 6px; align-items: center; margin-top: 10px; padding: 5px 12px; border-radius: 999px;
  background: var(--mv-teal-bg); color: var(--mv-teal); font-size: .76rem; font-weight: 600; }

@media (max-width: 640px) {   /* phones: everything stacks, except image pairs and the sample gallery (2 per row) */
  :is(.st-key-mv_images, .st-key-mv_examples) [data-testid="stHorizontalBlock"] { flex-direction: row; flex-wrap: wrap; }
  :is(.st-key-mv_images, .st-key-mv_examples) [data-testid="stColumn"] { flex: 1 1 calc(50% - .5rem) !important;
    min-width: calc(50% - .5rem) !important; width: calc(50% - .5rem) !important; }
  .mv-finding .t { font-size: 1.2rem; }
  [data-testid="stMainBlockContainer"], .block-container { padding-left: 1rem; padding-right: 1rem; }
}
/* ---------------------------------------------------------------- sign-in */
.st-key-mv_login { background: var(--mv-card); border: 1px solid var(--mv-line); border-radius: 24px;
  box-shadow: 0 20px 50px rgba(19,24,55,.10); padding: 34px 32px 26px; margin-top: 6vh; }
.mv-login-head { text-align: center; }
.mv-login-head img { width: 60px; height: 60px; border-radius: 16px; box-shadow: 0 10px 24px rgba(27,34,70,.18); }
.mv-login-head .brand { margin-top: 14px; font-family: 'JetBrains Mono', monospace; font-size: .78rem; font-weight: 600;
  letter-spacing: .28em; color: var(--mv-gold-ink); text-transform: uppercase; }
.mv-login-head .sub { margin-top: 4px; font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .2em;
  text-transform: uppercase; color: var(--mv-muted); }
.mv-login-title { text-align: center; font-size: 1.45rem !important; margin: 22px 0 4px !important; padding: 0 !important; }
.mv-login-text { text-align: center; color: var(--mv-ink-2); font-size: .92rem; margin: 0 0 14px; }
.st-key-mv_login input { font-family: 'JetBrains Mono', monospace !important; letter-spacing: .08em; text-align: center;
  font-size: 1rem !important; }
.mv-login-foot { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--mv-line); color: var(--mv-muted);
  font-size: .8rem; line-height: 1.55; text-align: center; }
.mv-login-foot b { color: var(--mv-ink-2); }

/* sidebar account panel */
.mv-account { border: 1px solid #2E3768; background: rgba(255,255,255,.04); border-radius: 14px; padding: 12px 14px;
  margin: 4px 0 2px; }
.mv-account .k { font-family: 'JetBrains Mono', monospace; font-size: .6rem; letter-spacing: .16em; text-transform: uppercase;
  color: #8D93B5; }
.mv-account .org { color: #fff; font-weight: 700; font-size: .92rem; margin-top: 4px; line-height: 1.3; }
.mv-account .meta { color: #B9BEDD; font-size: .76rem; margin-top: 4px; }
.mv-account .ok { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #3CCB9E; margin-right: 6px; }
/* sidebar brand */
.mv-sbrand { margin: -18px 0 14px; padding-bottom: 14px; border-bottom: 1px solid #2E3768; }
.mv-sbrand .row { display: flex; align-items: center; gap: 12px; }
.mv-sbrand img { width: 42px; height: 42px; border-radius: 12px; flex: none; }
.mv-sbrand .name { font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 600; letter-spacing: .2em;
  color: var(--mv-gold); }
.mv-sbrand .tag { margin-top: 10px; font-family: 'JetBrains Mono', monospace; font-size: .64rem; font-weight: 500;
  letter-spacing: .14em; text-transform: uppercase; color: #9EA4C7; white-space: nowrap; }
/* ---------------------------------------------------------------- consultations */
.mv-consult-head { margin: 4px 0 18px; padding-bottom: 18px; border-bottom: 1px solid var(--mv-line); }
.mv-consult-head h1 { font-size: clamp(1.6rem, 3.2vw, 2.2rem) !important; margin: 4px 0 0 !important; padding: 0 !important; }
.mv-consult-head p { color: var(--mv-ink-2); max-width: 46rem; margin: 8px 0 0; line-height: 1.6; }
.st-key-mv_consult_share, [class*="st-key-mv_spec_"] { background: var(--mv-card); border: 1px solid var(--mv-line);
  border-radius: var(--mv-radius); box-shadow: var(--mv-shadow); padding: 18px 20px; }
[class*="st-key-mv_spec_"] { height: 100%; }
[class*="st-key-mv_spec_"] [data-testid="stMarkdownContainer"], [class*="st-key-mv_spec_"] [data-testid="stMarkdown"] { margin-bottom: 0 !important; }
.mv-spec .top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.mv-spec .av { width: 48px; height: 48px; border-radius: 14px; display: grid; place-items: center; font-weight: 800;
  letter-spacing: .04em; color: var(--mv-gold-2); background: linear-gradient(135deg, var(--mv-navy-2), var(--mv-navy)); }
.mv-example { font-size: .66rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--mv-amber);
  background: #FDF4E3; padding: 4px 9px; border-radius: 999px; }
.mv-spec .tt { margin-top: 14px; font-weight: 700; font-size: 1.02rem; color: var(--mv-ink); line-height: 1.3; min-height: 2.6em; }
.mv-spec .nm { color: var(--mv-ink-2); font-size: .88rem; margin-top: 2px; }
.mv-spec .fc { color: var(--mv-ink-2); font-size: .86rem; line-height: 1.5; margin-top: 8px; min-height: 3em; }
.mv-spec .meta { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 12px 0 4px; color: var(--mv-muted); font-size: .78rem; }
.st-key-mv_calendar { background: var(--mv-card); border: 1px solid var(--mv-line); border-radius: var(--mv-radius);
  box-shadow: var(--mv-shadow); padding: 6px; overflow: hidden; }
.st-key-mv_calendar iframe { border-radius: 14px; }
/* ---------------------------------------------------------------- appointments */
.mv-emergency { border: 1px solid #F3C4CA; background: var(--mv-rose-bg); color: #8E2B37; border-radius: 14px;
  padding: 10px 14px; font-size: .86rem; line-height: 1.5; margin: 0 0 8px; }
.mv-emergency b { color: var(--mv-rose); }
.mv-dept { font-size: .7rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--mv-indigo);
  background: #EEF0FB; padding: 4px 9px; border-radius: 999px; }
.st-key-mv_appt_form { background: var(--mv-card); border: 1px solid var(--mv-line); border-radius: var(--mv-radius);
  box-shadow: var(--mv-shadow); padding: 20px 22px; }
[class*="st-key-mv_req_"], [class*="st-key-mv_tri_"] { background: var(--mv-card); border: 1px solid var(--mv-line);
  border-radius: 18px; box-shadow: var(--mv-shadow); padding: 16px 20px 10px; margin-bottom: 4px; }
.mv-req .hd { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.mv-req .tt { margin-top: 8px; font-weight: 700; color: var(--mv-ink); }
.mv-req .sub { color: var(--mv-muted); font-size: .82rem; margin-top: 2px; }
.mv-req .when { color: var(--mv-ink-2); font-size: .9rem; margin-top: 6px; }
.mv-req-note { margin-top: 6px; font-size: .84rem; color: var(--mv-ink-2); background: #F8F9FD; border-radius: 10px; padding: 6px 10px; }
.mv-req-detail { display: grid; gap: 4px; margin-top: 10px; font-size: .86rem; color: var(--mv-ink-2); }
.mv-req-detail .kv span { display: inline-block; min-width: 92px; font-family: 'JetBrains Mono', monospace; font-size: .64rem;
  letter-spacing: .1em; text-transform: uppercase; color: var(--mv-muted); }
.mv-urg, .mv-status, .mv-pos { font-size: .72rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; }
.mv-urg.urgent { color: #fff; background: var(--mv-rose); }
.mv-urg.soon { color: var(--mv-amber); background: #FDF4E3; }
.mv-urg.routine { color: var(--mv-ink-2); background: #EEF0F6; }
.mv-pos { color: #fff; background: var(--mv-navy); }
.mv-status.pending { color: var(--mv-indigo); background: #EEF0FB; }
.mv-status.confirmed { color: var(--mv-teal); background: var(--mv-teal-bg); }
.mv-status.declined, .mv-status.cancelled { color: var(--mv-muted); background: #F0F1F5; }
.mv-status.completed { color: var(--mv-ink-2); background: #EEF0F6; }
/* ---------------------------------------------------------------- left panel: grouped navigation */
.mv-navsec { font-family: 'JetBrains Mono', monospace; font-size: .6rem; font-weight: 500; letter-spacing: .18em;
  text-transform: uppercase; color: #7D84AA; margin: 12px 0 2px 10px; }
.st-key-mv_nav [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
/* ---------------------------------------------------------------- platform overview */
[class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"] { background: var(--mv-card); border: 1px solid var(--mv-line);
  border-radius: var(--mv-radius); box-shadow: var(--mv-shadow); padding: 22px 22px 14px; height: 100%; }
:is([class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"]) [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.mv-mod .top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.mv-mod .ic { width: 48px; height: 48px; border-radius: 14px; display: grid; place-items: center; font-size: 1.5rem;
  color: var(--mv-gold-2); background: linear-gradient(135deg, var(--mv-navy-2), var(--mv-navy)); }
.mv-mod h3 { font-size: 1.2rem !important; margin: 16px 0 6px !important; padding: 0 !important; }
.mv-mod p, .mv-feat p { color: var(--mv-ink-2); font-size: .9rem; line-height: 1.6; margin: 0; }
.mv-mod .kp { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0 6px; }
.mv-mod .kp div { background: #F8F9FD; border: 1px solid var(--mv-line); border-radius: 14px; padding: 10px 12px; min-width: 0; }
.mv-mod .kp b { display: block; font-size: 1.15rem; font-weight: 800; color: var(--mv-ink); }
.mv-mod .kp span { font-size: .7rem; color: var(--mv-muted); line-height: 1.3; display: block; }
.mv-feat .k { font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--mv-gold-ink); }
.mv-feat h4 { font-size: 1rem; font-weight: 700; color: var(--mv-ink); margin: 8px 0 6px; padding: 0; }
@media (max-width: 640px) { .mv-mod .kp { gap: 6px; } }
/* ---------------------------------------------------------------- brain MRI results */
.mv-kpi .meter.risk span { background: linear-gradient(90deg, #6FCBB2 0%, #E6B651 50%, var(--mv-rose) 100%); }
.mv-kpi .v.low { color: var(--mv-teal); } .mv-kpi .v.medium { color: var(--mv-amber); } .mv-kpi .v.high { color: var(--mv-rose); }
.mv-finding.amber .ic { background: #FDF4E3; color: var(--mv-amber); } .mv-finding.amber .t { color: var(--mv-amber); }
.st-key-mv_bb, .st-key-mv_cl, .st-key-mv_bimages, .st-key-mv_breasons, .st-key-mv_bprobs, .st-key-mv_bmorph { background: var(--mv-card);
  border: 1px solid var(--mv-line); border-radius: var(--mv-radius); box-shadow: var(--mv-shadow); padding: 20px 22px; }
:is(.st-key-mv_bb, .st-key-mv_cl, .st-key-mv_bimages, .st-key-mv_breasons, .st-key-mv_bprobs, .st-key-mv_bmorph) [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important; }
.mv-table { width: 100%; border-collapse: collapse; font-size: .84rem; color: var(--mv-ink-2); }
.mv-table th { font-family: 'JetBrains Mono', monospace; font-size: .6rem; font-weight: 500; letter-spacing: .12em;
  text-transform: uppercase; color: var(--mv-muted); text-align: left; padding: 6px 8px 8px 0; border-bottom: 1px solid var(--mv-line); }
.mv-table td { padding: 8px 8px 8px 0; border-bottom: 1px solid var(--mv-line); vertical-align: middle; }
.mv-table tr:last-child td { border-bottom: none; }
.mv-table .num { font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: var(--mv-ink); text-align: right; }
.mv-table th.num { font-size: .6rem; color: var(--mv-muted); }
.mv-table tr.sel td { color: var(--mv-ink); font-weight: 700; }
.mv-tag { font-size: .7rem; font-weight: 700; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }
.mv-tag.yes { color: var(--mv-rose); background: var(--mv-rose-bg); }
.mv-tag.no { color: var(--mv-teal); background: var(--mv-teal-bg); }
/* ---------------------------------------------------------------- benchmarks */
.st-key-mv_graphs [data-testid="stImage"] img { background: #fff; border: 1px solid var(--mv-line); }
[class*="st-key-mv_bench_"] { background: var(--mv-card);
  border: 1px solid var(--mv-line); border-radius: var(--mv-radius); box-shadow: var(--mv-shadow); padding: 18px 22px; height: 100%; }
[class*="st-key-mv_bench_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
/* ================================================================ design layer: display type, pills, cards, motion */
/* display serif for titles and findings; body stays Plus Jakarta Sans */
:is(.mv-land h1, .mv-consult-head h1, .mv-mod h3, .mv-chat-hero h1, .mv-login-title, .mv-h h3) {
  font-family: 'Fraunces', Georgia, serif !important; font-weight: 600 !important; letter-spacing: -.015em !important; }
.mv-finding .t, .mv-feat h4, .mv-panel-title { font-family: 'Fraunces', Georgia, serif; font-weight: 600; letter-spacing: -.01em; }
.mv-consult-head h1 { font-size: clamp(1.9rem, 3.6vw, 2.6rem) !important; }
.mv-h { margin: 34px 0 14px; }
.mv-h h3 { font-size: 1.45rem !important; }

/* pill tags */
.mv-pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px;
  font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--mv-navy-2);
  background: #E9ECFA; border: 1px solid #DCE0F5; }
.mv-pill i { width: 7px; height: 7px; border-radius: 50%; background: var(--mv-gold); box-shadow: 0 0 0 0 rgba(201,168,106,.6);
  animation: mv-ping 2.4s ease-out infinite; }
.mv-pill.gold { color: var(--mv-gold-ink); background: #FBF4E4; border-color: #F0DDB0; }
.mv-pill.rose { color: var(--mv-rose); background: var(--mv-rose-bg); border-color: #F6CDD3; }
.mv-pill.teal { color: var(--mv-teal); background: var(--mv-teal-bg); border-color: #C9EBE2; }
.mv-consult-head .mv-label { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; margin: 0 0 12px;
  border-radius: 999px; font-family: 'Plus Jakarta Sans', sans-serif; font-size: .68rem; font-weight: 700;
  letter-spacing: .08em; color: var(--mv-navy-2); background: #E9ECFA; border: 1px solid #DCE0F5; }
.mv-consult-head .mv-label::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--mv-gold); }

/* landing hero */
.mv-land { text-align: center; padding: 3vh 0 8px; }
.mv-land h1 { font-size: clamp(2.3rem, 5.4vw, 4rem) !important; line-height: 1.04 !important; margin: 18px auto 0 !important;
  padding: 0 !important; max-width: 13em; color: var(--mv-ink) !important; }
.mv-land h1 em { font-style: italic; color: var(--mv-gold-ink); }
.mv-land p { color: var(--mv-ink-2); max-width: 38rem; margin: 18px auto 0; line-height: 1.7; font-size: 1.05rem; }
.st-key-mv_cta [data-testid="stHorizontalBlock"] { justify-content: center; }
.st-key-mv_cta [data-testid="stColumn"] { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.st-key-mv_cta .stButton > button { border-radius: 999px; padding: 10px 22px; min-height: 46px; }
.st-key-mv_cta .stButton > button[kind="secondary"] { background: var(--mv-card); border: 1.5px solid var(--mv-line-2); }
.st-key-mv_cta .stButton > button[kind="secondary"]:hover { border-color: var(--mv-navy-2); color: var(--mv-navy-2); }
.mv-trust { display: flex; justify-content: center; flex-wrap: wrap; gap: 14px 40px; margin: 34px 0 6px; padding: 18px 0;
  border-top: 1px solid var(--mv-line); border-bottom: 1px solid var(--mv-line); }
.mv-trust div { text-align: center; }
.mv-trust b { display: block; font-family: 'Fraunces', Georgia, serif; font-size: 1.9rem; font-weight: 600; color: var(--mv-ink); }
.mv-trust span { font-family: 'JetBrains Mono', monospace; font-size: .6rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--mv-muted); }

/* clickable sample cards: st.container(key="mv_card_...") with markup + an invisible full-size button */
[class*="st-key-mv_card_"] { position: relative; background: var(--mv-card); border: 1px solid var(--mv-line);
  border-radius: 18px; padding: 12px 14px; box-shadow: var(--mv-shadow); gap: 0;
  transition: transform .22s cubic-bezier(.2,.7,.2,1), box-shadow .22s ease, border-color .22s ease; }
[class*="st-key-mv_card_"]:hover { transform: translateY(-3px); border-color: #C9CFF0;
  box-shadow: 0 2px 4px rgba(19,24,55,.04), 0 16px 34px rgba(42,51,117,.14); }
[class*="st-key-mv_card_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="st-key-mv_card_"] .stButton { position: absolute; inset: 0; z-index: 3; }
[class*="st-key-mv_card_"] [data-testid="stElementContainer"]:has(.stButton) { position: static; }
[class*="st-key-mv_card_"] .stButton :is(button, [data-testid="stTooltipHoverTarget"], [data-testid="stTooltipHoverTarget"] > div) { width: 100% !important; height: 100% !important; }
[class*="st-key-mv_card_"] .stButton button { opacity: 0; cursor: pointer; }
.mv-sample { display: flex; align-items: center; gap: 12px; min-width: 0; }
.mv-sample img { width: 52px; height: 52px; flex: none; border-radius: 50%; object-fit: cover;
  box-shadow: 0 0 0 3px #fff, 0 0 0 5px var(--ring, #DCE0F5); transition: transform .3s ease; }
[class*="st-key-mv_card_"]:hover .mv-sample img { transform: scale(1.06) rotate(-2deg); }
.mv-sample > div:nth-child(2) { min-width: 0; overflow-wrap: break-word; }
.mv-sample:not(.big) .go { display: none; }
.mv-sample:not(.big) { gap: 10px; }
.mv-sample:not(.big) img { width: 42px; height: 42px; }
.mv-sample:not(.big) b { font-size: .8rem; }
[class*="st-key-mv_card_"]:has(.mv-sample:not(.big)) { padding: 10px 10px; }
.mv-sample b { display: block; font-size: .86rem; font-weight: 700; color: var(--mv-ink); line-height: 1.25; }
.mv-sample span { display: inline-block; margin-top: 4px; font-family: 'JetBrains Mono', monospace; font-size: .58rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--mv-muted); }
.mv-sample.big { flex-direction: row; }
.mv-sample.big img { width: 64px; height: 64px; }
.mv-sample.big b { font-family: 'Fraunces', Georgia, serif; font-size: 1.02rem; font-weight: 600; }
.mv-sample .go { margin-left: auto; width: 30px; height: 30px; flex: none; border-radius: 50%; display: grid; place-items: center;
  background: #EEF0FB; color: var(--mv-navy-2); font-size: .9rem; transition: transform .22s ease, background .22s ease; }
[class*="st-key-mv_card_"]:hover .mv-sample .go { transform: translateX(3px); background: var(--mv-navy); color: var(--mv-gold-2); }

/* modality and feature cards: circle arrow, hover lift */
[class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"] { transition: transform .22s cubic-bezier(.2,.7,.2,1), box-shadow .22s ease; }
[class*="st-key-mv_mod_"]:hover, [class*="st-key-mv_feat_"]:hover { transform: translateY(-4px);
  box-shadow: 0 2px 4px rgba(19,24,55,.04), 0 20px 40px rgba(42,51,117,.13); }
.st-key-mv_mod_brain { background: linear-gradient(160deg, #FFFFFF 55%, #EEF0FB 100%); }
.st-key-mv_mod_crc { background: linear-gradient(160deg, #FFFFFF 55%, #FBF4E4 100%); }
:is([class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"]) [data-testid="stPageLink"] a { border-radius: 999px;
  background: var(--mv-navy); padding: 4px 16px; width: fit-content; transition: background .2s ease, transform .2s ease; }
:is([class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"]) [data-testid="stPageLink"] a span { color: #fff !important; }
:is([class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"]) [data-testid="stPageLink"] a:hover { background: var(--mv-navy-2);
  transform: translateX(2px); }
.mv-feat .top { display: flex; align-items: center; justify-content: space-between; }
.mv-feat h4 { font-size: 1.22rem; margin: 16px 0 8px; line-height: 1.25; }

/* scan viewer */
.mv-panel-title { font-size: 1.2rem; color: var(--mv-ink); margin: 0 0 12px; }
.st-key-mv_bimages [data-testid="stSegmentedControl"] button, .st-key-mv_bimages [data-baseweb="button-group"] button {
  border-radius: 999px !important; }
.mv-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 4px; }
.mv-metrics div { background: #F8F9FD; border: 1px solid var(--mv-line); border-radius: 14px; padding: 10px 12px; min-width: 0; }
.mv-metrics span { display: block; font-family: 'JetBrains Mono', monospace; font-size: .58rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--mv-muted); }
.mv-metrics b { display: block; margin-top: 4px; font-size: 1.05rem; font-weight: 700; color: var(--mv-ink); }

/* footer */
.mv-footer { margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--mv-line); display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 8px 24px; font-size: .78rem; color: var(--mv-muted); }
.mv-footer b { color: var(--mv-ink-2); }

/* ---------------------------------------------------------------- motion */
@keyframes mv-rise { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
@keyframes mv-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes mv-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes mv-ping { 0% { box-shadow: 0 0 0 0 rgba(201,168,106,.55); } 70%, 100% { box-shadow: 0 0 0 9px rgba(201,168,106,0); } }
@keyframes mv-sheen { from { background-position: 200% 0; } to { background-position: -200% 0; } }
.mv-land > *, .mv-consult-head > * { animation: mv-rise .7s cubic-bezier(.2,.7,.2,1) both; }
.mv-land > *:nth-child(2), .mv-consult-head > *:nth-child(2) { animation-delay: .08s; }
.mv-land > *:nth-child(3), .mv-consult-head > *:nth-child(3) { animation-delay: .16s; }
.mv-result, .mv-trust, [class*="st-key-mv_card_"], [class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"],
:is(.st-key-mv_images, .st-key-mv_probs, .st-key-mv_reasons, .st-key-mv_bimages, .st-key-mv_breasons, .st-key-mv_bprobs,
    .st-key-mv_bb, .st-key-mv_cl, .st-key-mv_bmorph, .st-key-mv_appt_form), [class*="st-key-mv_bench_"], [class*="st-key-mv_spec_"] {
  animation: mv-rise .6s cubic-bezier(.2,.7,.2,1) both; }
[data-testid="stColumn"]:nth-child(2) > div > :is([class*="st-key-mv_card_"], [class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"]) { animation-delay: .06s; }
[data-testid="stColumn"]:nth-child(3) > div > :is([class*="st-key-mv_card_"], [class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"]) { animation-delay: .12s; }
[data-testid="stColumn"]:nth-child(4) > div > [class*="st-key-mv_card_"] { animation-delay: .18s; }
[data-testid="stColumn"]:nth-child(5) > div > [class*="st-key-mv_card_"] { animation-delay: .24s; }
.mv-prob .fill, .mv-kpi .meter span { transform-origin: left; animation: mv-grow 1s cubic-bezier(.2,.7,.2,1) .15s both; }
.mv-finding .ic { animation: mv-fade .5s ease .1s both; }
.mv-land h1 em { background: linear-gradient(100deg, var(--mv-gold-ink) 30%, #D8BC85 50%, var(--mv-gold-ink) 70%);
  background-size: 200% 100%; -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: mv-sheen 6s linear infinite; }
.st-key-mv_nav a { transition: background .18s ease, transform .18s ease; }
.st-key-mv_nav a:hover { transform: translateX(3px); }
[data-testid="stMainBlockContainer"] .stButton > button, .stDownloadButton > button { transition: transform .18s ease, box-shadow .18s ease, background .18s ease; }
[data-testid="stMainBlockContainer"] .stButton > button:active { transform: scale(.98); }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .mv-land h1 em { color: var(--mv-gold-ink); background: none; }
}
@media (max-width: 640px) { .mv-trust { gap: 12px 24px; } .mv-trust b { font-size: 1.5rem; } .mv-metrics { grid-template-columns: 1fr 1fr; } }
/* ================================================================ atlas layer: a clinical atlas / reading-room look.
   Graph-paper canvas, ink rules instead of shadows, numbered sections, film plates with gold registration marks. */
:root {
  --mv-radius: 12px;
  --mv-shadow: 0 1px 0 rgba(19,24,55,.04);
  --mk: rgba(201,168,106,.95);
  --mv-plate: linear-gradient(var(--mk), var(--mk)) left 5px top 5px / 16px 1.5px,
    linear-gradient(var(--mk), var(--mk)) left 5px top 5px / 1.5px 16px,
    linear-gradient(var(--mk), var(--mk)) right 5px top 5px / 16px 1.5px,
    linear-gradient(var(--mk), var(--mk)) right 5px top 5px / 1.5px 16px,
    linear-gradient(var(--mk), var(--mk)) left 5px bottom 5px / 16px 1.5px,
    linear-gradient(var(--mk), var(--mk)) left 5px bottom 5px / 1.5px 16px,
    linear-gradient(var(--mk), var(--mk)) right 5px bottom 5px / 16px 1.5px,
    linear-gradient(var(--mk), var(--mk)) right 5px bottom 5px / 1.5px 16px, #0B0F24;
}
[data-testid="stMain"] {
  background-image: linear-gradient(rgba(27,34,70,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(27,34,70,.035) 1px, transparent 1px);
  background-size: 28px 28px; }

/* kickers replace pills: gold rule + spaced mono caps */
.mv-pill, .mv-consult-head .mv-label { background: none !important; border: 0 !important; padding: 0 !important;
  border-radius: 0 !important; gap: 12px; color: var(--mv-gold-ink) !important; font-family: 'JetBrains Mono', monospace !important;
  font-size: .64rem !important; font-weight: 600 !important; letter-spacing: .22em !important; }
.mv-pill::before, .mv-consult-head .mv-label::before { content: ""; width: 28px !important; height: 1px !important;
  border-radius: 0 !important; background: var(--mv-gold) !important; flex: none; }
.mv-pill i { display: none; }
.mv-pill.rose { color: var(--mv-rose) !important; } .mv-pill.rose::before { background: var(--mv-rose) !important; }
.mv-pill.teal { color: var(--mv-teal) !important; } .mv-pill.teal::before { background: var(--mv-teal) !important; }

/* page header: heavy ink rule on top, like a journal section */
.mv-consult-head { border-top: 2px solid var(--mv-ink); padding-top: 16px; }
.mv-consult-head h1 { font-weight: 500 !important; letter-spacing: -.03em !important; font-size: clamp(2.2rem, 4.4vw, 3.2rem) !important; }

/* numbered sections */
[data-testid="stMainBlockContainer"] { counter-reset: mvsec; }
.mv-h { border-top: 1px solid var(--mv-line-2); padding-top: 12px; margin-top: 38px; }
.mv-h h3 { font-weight: 500 !important; }
.mv-h h3::before { counter-increment: mvsec; content: counter(mvsec, decimal-leading-zero); font-family: 'JetBrains Mono', monospace;
  font-size: .66rem; font-weight: 600; letter-spacing: .12em; color: var(--mv-gold-ink); margin-right: 14px;
  position: relative; top: -.35em; }
.mv-h span { font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .12em; text-transform: uppercase; }

/* cards: hairlines, not floating shadows */
.mv-result, .st-key-mv_images, .st-key-mv_probs, .st-key-mv_reasons, .st-key-mv_bimages, .st-key-mv_breasons,
.st-key-mv_bprobs, .st-key-mv_bb, .st-key-mv_cl, .st-key-mv_bmorph, .st-key-mv_appt_form, [class*="st-key-mv_bench_"],
[class*="st-key-mv_spec_"], [class*="st-key-mv_req_"], [class*="st-key-mv_tri_"], [class*="st-key-mv_card_"],
[class*="st-key-mv_mod_"], [class*="st-key-mv_feat_"], .st-key-mv_login {
  border-radius: 10px !important; box-shadow: none !important; border-color: var(--mv-line-2) !important; }
.mv-result { border-top: 3px solid var(--mv-ink) !important; }
.mv-finding .t { font-size: 1.8rem; font-weight: 500; letter-spacing: -.02em; }
.mv-finding .ic { border-radius: 50%; }
.mv-kpi { border-radius: 6px; background: transparent; border: 0; border-left: 1px solid var(--mv-line-2); padding: 4px 0 4px 14px; }
.mv-kpis { gap: 0 18px; }
.mv-kpi .v.big { font-family: 'Fraunces', Georgia, serif; font-weight: 500; font-size: 2rem; }

/* ruler gauge: tick marks every 10%, a hairline baseline and a ring marker */
.mv-kpi .meter { height: 14px; border-radius: 0; overflow: visible; position: relative; margin-top: 10px;
  background: repeating-linear-gradient(90deg, var(--mv-line-2) 0 1px, transparent 1px 10%) 0 0 / 100% 6px no-repeat,
              linear-gradient(var(--mv-line-2), var(--mv-line-2)) 0 100% / 100% 1px no-repeat; }
.mv-kpi .meter span { position: relative; height: 3px; margin-top: 8px; border-radius: 0; color: var(--mv-rose); overflow: visible; }
.mv-kpi .meter.risk span { color: var(--mv-navy); }
.mv-kpi .meter span::after { content: ""; position: absolute; right: -6px; top: -5px; width: 9px; height: 9px; border-radius: 50%;
  background: var(--mv-bg); border: 2px solid currentColor; }
.mv-prob .track { height: 4px; border-radius: 0; }
.mv-prob .fill { border-radius: 0; }

/* film plates with registration marks around every result image */
:is(.st-key-mv_images, .st-key-mv_bimages) [data-testid="stImage"] { background: var(--mv-plate); background-repeat: no-repeat;
  padding: 12px; border-radius: 4px; }
:is(.st-key-mv_images, .st-key-mv_bimages) [data-testid="stImage"] img { border-radius: 1px !important; }
:is(.st-key-mv_images, .st-key-mv_bimages) .mv-label { color: var(--mv-ink-2); }

/* sample cards: squarer */
[class*="st-key-mv_card_"] { border-radius: 8px !important; }
.mv-sample img { box-shadow: 0 0 0 2px #fff, 0 0 0 3px var(--ring, #DCE0F5); }

/* buttons: squared, ink */
[data-testid="stMainBlockContainer"] .stButton > button, .stDownloadButton > button { border-radius: 6px; }
[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"] { background: var(--mv-ink) !important;
  box-shadow: none !important; }
[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover { background: var(--mv-navy-2) !important; }

/* left panel: numbered entries, gold bar on the open page */
.st-key-mv_nav { counter-reset: mvnav; }
.st-key-mv_nav a { position: relative; }
.st-key-mv_nav a::after { counter-increment: mvnav; content: counter(mvnav, decimal-leading-zero); margin-left: auto;
  padding-left: 8px; font-family: 'JetBrains Mono', monospace; font-size: .58rem; letter-spacing: .1em; color: #5F678F; }
.st-key-mv_nav a[aria-current="page"]::before { content: ""; position: absolute; left: -10px; top: 22%; bottom: 22%;
  width: 2px; background: var(--mv-gold); }
.st-key-mv_nav a[aria-current="page"]::after { color: var(--mv-gold); }

[data-testid="stHeaderActionElements"] { display: none !important; }
/* ---------------------------------------------------------------- platform: atlas spread */
.mv-mast2 { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 0 0 10px;
  border-bottom: 2px solid var(--mv-ink); font-family: 'JetBrains Mono', monospace; font-size: .6rem; letter-spacing: .18em;
  text-transform: uppercase; color: var(--mv-ink-2); }
.mv-mast2 b { color: var(--mv-gold-ink); font-weight: 600; }
.mv-atlas { padding: 34px 0 0; }
.mv-atlas h1 { font-family: 'Fraunces', Georgia, serif !important; font-weight: 500 !important; color: var(--mv-ink) !important;
  font-size: clamp(2.3rem, 3.9vw, 3.9rem) !important; line-height: 1 !important; letter-spacing: -.035em !important;
  margin: 18px 0 0 !important; padding: 0 !important; }
.mv-atlas h1 em { font-style: italic; color: var(--mv-gold-ink); padding-bottom: .04em;
  background: linear-gradient(var(--mv-gold), var(--mv-gold)) no-repeat 0 100% / 100% .06em;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; animation: mv-underline 1.3s cubic-bezier(.2,.7,.2,1) .6s both; }
@keyframes mv-underline { from { background-size: 0 .06em; } to { background-size: 100% .06em; } }
.mv-atlas .lede { font-size: 1.06rem; line-height: 1.75; color: var(--mv-ink-2); max-width: 31rem; margin: 26px 0 0; }
.mv-atlas .lede::first-letter { float: left; font-family: 'Fraunces', Georgia, serif; font-size: 3.4em; line-height: .82;
  padding: 6px 10px 0 0; color: var(--mv-navy); }
.st-key-mv_cta2 { margin-top: 18px; }
.st-key-mv_cta2 [data-testid="stHorizontalBlock"] { gap: 28px; }
.st-key-mv_cta2 [data-testid="stColumn"] { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.st-key-mv_cta2 .stButton > button { background: none !important; border: 0 !important; border-radius: 0 !important;
  border-bottom: 1.5px solid var(--mv-ink) !important; padding: 4px 0 !important; min-height: 0 !important;
  color: var(--mv-ink) !important; font-weight: 700; box-shadow: none !important; }
.st-key-mv_cta2 .stButton > button:hover { color: var(--mv-gold-ink) !important; border-color: var(--mv-gold) !important;
  transform: none !important; }
.st-key-mv_cta2 .stButton > button p { font-size: .95rem; }

.mv-lightbox { margin: 30px 0 0; }
.mv-lightbox .plate { position: relative; aspect-ratio: 1 / 1; background: var(--mv-plate); background-repeat: no-repeat;
  border-radius: 6px; overflow: hidden; box-shadow: 0 34px 60px -28px rgba(11,15,36,.65); }
.mv-lightbox .plate img { position: absolute; inset: 16px; width: calc(100% - 32px); height: calc(100% - 32px);
  object-fit: cover; border-radius: 2px; }
.mv-lightbox .ovl { animation: mv-reveal 7s ease-in-out infinite; }
.mv-lightbox .scan { position: absolute; left: 16px; right: 16px; top: 0; height: 28%; pointer-events: none; z-index: 2;
  background: linear-gradient(180deg, rgba(240,221,176,0) 0%, rgba(240,221,176,.10) 80%, rgba(240,221,176,.55) 99%, #F0DDB0 100%);
  animation: mv-scan 7s cubic-bezier(.45,.05,.55,.95) infinite; }
.mv-lightbox .hud { position: absolute; z-index: 3; font-family: 'JetBrains Mono', monospace; font-size: .56rem;
  letter-spacing: .14em; text-transform: uppercase; color: rgba(233,226,210,.78); line-height: 1.7; }
.mv-lightbox .hud b { color: var(--mv-gold-2); font-weight: 600; }
.mv-lightbox .tl { top: 24px; left: 26px; } .mv-lightbox .tr { top: 24px; right: 26px; text-align: right; }
.mv-lightbox .bl { bottom: 24px; left: 26px; } .mv-lightbox .br { bottom: 24px; right: 26px; text-align: right; }
.mv-lightbox .rec { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--mv-rose);
  margin-right: 6px; animation: mv-blink 1.4s steps(2, start) infinite; }
.mv-lightbox figcaption { margin-top: 14px; padding-left: 12px; border-left: 2px solid var(--mv-gold); font-size: .8rem;
  line-height: 1.55; color: var(--mv-ink-2); }
.mv-lightbox figcaption b { font-family: 'Fraunces', Georgia, serif; font-style: italic; font-weight: 600; color: var(--mv-ink); }

.mv-figs { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin: 46px 0 6px; border-top: 2px solid var(--mv-ink);
  border-bottom: 1px solid var(--mv-line-2); }
.mv-figs div { padding: 16px 16px 16px 18px; border-left: 1px solid var(--mv-line-2); min-width: 0; }
.mv-figs div:first-child { border-left: 0; padding-left: 0; }
.mv-figs b { display: block; font-family: 'Fraunces', Georgia, serif; font-size: 2.5rem; font-weight: 500; line-height: 1;
  letter-spacing: -.03em; color: var(--mv-ink); white-space: nowrap; }
.mv-figs b sup { font-family: 'JetBrains Mono', monospace; font-size: .32em; font-weight: 600; color: var(--mv-gold-ink);
  letter-spacing: 0; margin-left: 4px; vertical-align: top; position: relative; top: .5em; }
.mv-figs span { display: block; margin-top: 8px; font-size: .8rem; color: var(--mv-ink-2); line-height: 1.4; }

/* index rows: whole row is a link (invisible full-size button, as on sample cards) */
[class*="st-key-mv_row_"] { position: relative; border-top: 1px solid var(--mv-line-2); padding: 22px 8px 22px 0; gap: 0;
  transition: background .3s ease; }
.st-key-mv_row_5 { border-bottom: 1px solid var(--mv-line-2); }
[class*="st-key-mv_row_"]:hover { background: linear-gradient(90deg, rgba(201,168,106,.10), rgba(201,168,106,0) 70%); }
[class*="st-key-mv_row_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.mv-row { display: grid; grid-template-columns: 64px minmax(0, 1.05fr) minmax(0, 1.5fr) 36px; gap: 22px; align-items: baseline; }
.mv-row .n { font-family: 'Fraunces', Georgia, serif; font-style: italic; font-size: 1.9rem; color: var(--mv-gold-ink); line-height: 1; }
.mv-row h3 { font-family: 'Fraunces', Georgia, serif !important; font-size: 1.65rem !important; font-weight: 500 !important;
  letter-spacing: -.02em !important; margin: 0 !important; padding: 0 !important; transition: transform .35s cubic-bezier(.2,.7,.2,1); }
.mv-row .k { margin-top: 8px; font-family: 'JetBrains Mono', monospace; font-size: .58rem; letter-spacing: .14em;
  text-transform: uppercase; color: var(--mv-muted); }
.mv-row p { margin: 0; color: var(--mv-ink-2); font-size: .9rem; line-height: 1.6; }
.mv-row .arr { justify-self: end; font-size: 1.3rem; color: var(--mv-ink); transition: transform .35s cubic-bezier(.2,.7,.2,1); }
[class*="st-key-mv_row_"]:hover .mv-row h3 { transform: translateX(8px); }
[class*="st-key-mv_row_"]:hover .mv-row .arr { transform: rotate(-45deg); color: var(--mv-gold-ink); }

/* plates: try a case */
[class*="st-key-mv_plate_"] { position: relative; gap: 0; }
[class*="st-key-mv_plate_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.mv-plt .frame { aspect-ratio: 4 / 3; background: var(--mv-plate); background-repeat: no-repeat; padding: 12px; border-radius: 4px;
  overflow: hidden; }
.mv-plt .frame img { width: 100%; height: 100%; object-fit: cover; border-radius: 1px; transition: transform .6s cubic-bezier(.2,.7,.2,1); }
[class*="st-key-mv_plate_"]:hover .mv-plt .frame img { transform: scale(1.06); }
.mv-plt .cap { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-top: 10px; }
.mv-plt .cap b { font-family: 'Fraunces', Georgia, serif; font-weight: 500; font-size: 1.05rem; color: var(--mv-ink); }
.mv-plt .cap b i { color: var(--mv-gold-ink); margin-right: 6px; }
.mv-plt .cap span { font-family: 'JetBrains Mono', monospace; font-size: .56rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--mv-muted); white-space: nowrap; }
[class*="st-key-mv_plate_"]:hover .mv-plt .cap span { color: var(--mv-gold-ink); }

/* invisible full-size buttons for rows and plates (same trick as sample cards) */
:is([class*="st-key-mv_row_"], [class*="st-key-mv_plate_"]) .stButton { position: absolute; inset: 0; z-index: 3; }
:is([class*="st-key-mv_row_"], [class*="st-key-mv_plate_"]) [data-testid="stElementContainer"]:has(.stButton) { position: static; }
:is([class*="st-key-mv_row_"], [class*="st-key-mv_plate_"]) .stButton :is(button, [data-testid="stTooltipHoverTarget"],
  [data-testid="stTooltipHoverTarget"] > div) { width: 100% !important; height: 100% !important; }
:is([class*="st-key-mv_row_"], [class*="st-key-mv_plate_"]) .stButton button { opacity: 0; cursor: pointer; }

/* motion for the spread */
@keyframes mv-scan { 0% { transform: translateY(-100%); } 60%, 100% { transform: translateY(360%); } }
@keyframes mv-reveal { 0%, 38% { opacity: 0; } 52%, 86% { opacity: 1; } 100% { opacity: 0; } }
@keyframes mv-blink { to { visibility: hidden; } }
@keyframes mv-wipe { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
.mv-mast2, .mv-atlas > *, .mv-figs, [class*="st-key-mv_row_"], [class*="st-key-mv_plate_"] {
  animation: mv-rise .8s cubic-bezier(.2,.7,.2,1) both; }
.mv-atlas > *:nth-child(2) { animation-delay: .1s; } .mv-atlas > *:nth-child(3) { animation-delay: .2s; }
.mv-lightbox { animation: mv-wipe 1.2s cubic-bezier(.7,0,.2,1) .2s both; }
.st-key-mv_row_2 { animation-delay: .06s; } .st-key-mv_row_3 { animation-delay: .12s; }
.st-key-mv_row_4 { animation-delay: .18s; } .st-key-mv_row_5 { animation-delay: .24s; }
@media (max-width: 1180px) {
  .mv-row { grid-template-columns: 44px 1fr 24px; }
  .mv-row p { grid-column: 2 / 3; }
  .mv-row .arr { grid-row: 1; grid-column: 3; }
}
@media (prefers-reduced-motion: reduce) { .mv-lightbox .ovl { opacity: 1; } .mv-lightbox .scan { display: none; } }
</style>
"""


@lru_cache(maxsize=None)
def logo_data_uri() -> str:
    import base64

    svg = (ASSETS_DIR / "logo.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def asset_uri(name: str) -> str:
    """Data URI of a file in assets/ (hero images)."""
    import base64
    data = (ASSETS_DIR / name).read_bytes()
    mime = "image/svg+xml" if name.endswith(".svg") else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def masthead_html() -> str:
    return ('<div class="mv-mast2"><span><b>MedVisionAI</b> · Clinical atlas</span>'
            '<span>Radiology &amp; pathology · research edition</span><span>Not a medical device</span></div>')


def atlas_html() -> str:
    """Platform headline, left aligned, with a drop-cap lede."""
    return ('<div class="mv-atlas"><span class="mv-pill">Clinical intelligence · est. 2026</span>'
            '<h1>Clinical Intelligence Platform for <em>medical imaging</em>.</h1>'
            '<p class="lede">Read a brain MRI slice or an H&amp;E tissue patch the way a specialist would: see what the '
            'model predicts, where it looked, how sure it is, and who should review the case next.</p></div>')


def lightbox_html() -> str:
    """A real MedVisionAI result on a light box: the slice, then the U-Net lesion outline fading in under a scan line."""
    return (f'<figure class="mv-lightbox"><div class="plate"><img src="{asset_uri("hero_mri.jpg")}" alt="Coronal T1 MRI"/>'
            f'<img class="ovl" src="{asset_uri("hero_mri_overlay.jpg")}" alt="U-Net lesion outline"/><span class="scan"></span>'
            '<span class="hud tl">BRISC 2025 · test<br/><b>T1 · coronal</b></span>'
            '<span class="hud tr">809 × 808<br/>U-Net · flip TTA</span>'
            '<span class="hud bl"><i class="rec"></i>Ensemble · 5 folds<br/><b>Meningioma 99.8%</b></span>'
            '<span class="hud br">Lesion 2.7% of slice<br/><b>Triage 29 / 100</b></span></div>'
            '<figcaption><b>Fig. 1</b> — Meningioma on a coronal T1 slice. The lesion outline (gold) comes from the '
            'U-Net; the class from the 5-fold EfficientNet ensemble. Real output of this app.</figcaption></figure>')


def figures_html() -> str:
    figs = (("99.3", "%", "brain MRI test accuracy, 5-fold ensemble, 1,000 held-out slices"),
            ("95.1", "%", "colorectal 9-class accuracy on 50 patients never seen in training"),
            ("100", "%", "colorectal tumour recall on the same external test set"),
            ("10,793", "n", "MRI slices in the BRISC 2025 comparative study"))
    return '<div class="mv-figs">' + "".join(f"<div><b>{v}<sup>{u}</sup></b><span>{t}</span></div>" for v, u, t in figs) + "</div>"


def row_html(n: str, title: str, kicker: str, text: str) -> str:
    """One entry of the platform index."""
    e = html.escape
    return (f'<div class="mv-row"><div class="n">{e(n)}</div><div><h3>{e(title)}</h3><div class="k">{e(kicker)}</div></div>'
            f'<p>{e(text)}</p><div class="arr">→</div></div>')


def plate_html(img_uri: str, numeral: str, title: str, tag: str) -> str:
    e = html.escape
    return (f'<div class="mv-plt"><div class="frame"><img src="{img_uri}" alt=""/></div><div class="cap">'
            f'<b><i>Pl. {e(numeral)}</i>{e(title)}</b><span>{e(tag)} →</span></div></div>')


def sample_html(img_uri: str, title: str, tag: str, ring: str = "#DCE0F5", big: bool = False) -> str:
    """Card body for a clickable sample: round thumbnail, title, small tag and an arrow."""
    e = html.escape
    return (f'<div class="mv-sample{" big" if big else ""}" style="--ring:{ring}"><img src="{img_uri}" alt=""/>'
            f'<div><b>{e(title)}</b><span>{e(tag)}</span></div><div class="go">→</div></div>')


@lru_cache(maxsize=64)
def thumb_uri(path: str, side: int = 128) -> str:
    """Small JPEG data URI of an image file, for card thumbnails."""
    import base64
    import io

    from PIL import Image

    img = Image.open(path).convert("RGB")
    img.thumbnail((side, side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def footer_html() -> str:
    return ('<div class="mv-footer"><div><b>MedVisionAI</b> · Clinical Intelligence Platform for medical imaging</div>'
            '<div>Research prototype · not a medical device · not for diagnosis</div></div>')


def page_head_html(label: str, title: str, text: str) -> str:
    """Header of every working page: small label, title, short description (trusted HTML)."""
    e = html.escape
    return f'<div class="mv-consult-head"><div class="mv-label">{e(label)}</div><h1>{e(title)}</h1><p>{text}</p></div>'


def section_html(title: str, note: str = "") -> str:
    return f'<div class="mv-h"><h3>{html.escape(title)}</h3><span>{html.escape(note)}</span></div>'


def chat_hero_html() -> str:
    return (f'<div class="mv-chat-hero"><img src="{logo_data_uri()}" alt=""/>'
            '<h1>How can I help with your case?</h1>'
            '<p>Ask about brain MRI, colorectal pathology, medical imaging or one of your MedVisionAI analyses.</p>'
            '<span class="mv-scope">● Medical and health questions only</span></div>')


def disclaimer_html(text: str) -> str:
    return f'<div class="mv-disclaimer"><b>Research use only.</b> {text}</div>'


def account_html(licence: dict) -> str:
    e = html.escape
    meta = " · ".join(x for x in (licence.get("plan") or "",
                                  f"valid until {licence['expires']}" if licence.get("expires") else "no expiry") if x)
    staff = ' · <b>hospital coordinator</b>' if licence.get("role") == "coordinator" else ""
    return (f'<div class="mv-account"><div class="k"><span class="ok"></span>Licensed to</div>'
            f'<div class="org">{e(licence.get("organisation", ""))}</div><div class="meta">{e(meta)}{staff}</div></div>')


def sidebar_brand_html() -> str:
    return (f'<div class="mv-sbrand"><div class="row"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/>'
            '<div class="name">MEDVISIONAI</div></div><div class="tag">Clinical Intelligence Platform</div></div>')

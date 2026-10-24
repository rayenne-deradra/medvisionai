"""Visual identity: MedVisionAI navy and gold, as a modern dashboard.

Navy sidebar, cool off-white canvas, white rounded cards with soft shadows, a gradient hero banner, one modern
sans-serif (Plus Jakarta Sans) with JetBrains Mono for small labels and numbers.
"""
from __future__ import annotations

import html
from functools import lru_cache

from ..config import ASSETS_DIR

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

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
</style>
"""


@lru_cache(maxsize=None)
def logo_data_uri() -> str:
    import base64

    svg = (ASSETS_DIR / "logo.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def hero_html() -> str:
    """Masthead: logo, platform name and headline. Deliberately quiet: no banner, no statistics."""
    return (f'<div class="mv-mast"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/><div>'
            '<div class="brand">MedVisionAI<span>Clinical Intelligence Platform</span></div>'
            '<h1>Early detection <em>saves lives<span class="stop">.</span></em></h1></div></div>')


def section_html(title: str, note: str = "") -> str:
    return f'<div class="mv-h"><h3>{html.escape(title)}</h3><span>{html.escape(note)}</span></div>'


def chat_hero_html() -> str:
    return (f'<div class="mv-chat-hero"><img src="{logo_data_uri()}" alt=""/>'
            '<h1>How can I help with your case?</h1>'
            '<p>Ask about colorectal pathology, medical imaging or one of your MedVisionAI analyses.</p>'
            '<span class="mv-scope">● Medical and health questions only</span></div>')


def disclaimer_html(text: str) -> str:
    return f'<div class="mv-disclaimer"><b>Research use only.</b> {text}</div>'


def account_html(licence: dict) -> str:
    e = html.escape
    meta = " · ".join(x for x in (licence.get("plan") or "",
                                  f"valid until {licence['expires']}" if licence.get("expires") else "no expiry") if x)
    return (f'<div class="mv-account"><div class="k"><span class="ok"></span>Licensed to</div>'
            f'<div class="org">{e(licence.get("organisation", ""))}</div><div class="meta">{e(meta)}</div></div>')


def sidebar_brand_html() -> str:
    return (f'<div class="mv-sbrand"><div class="row"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/>'
            '<div class="name">MEDVISIONAI</div></div><div class="tag">Clinical Intelligence Platform</div></div>')

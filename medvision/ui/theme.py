"""Visual identity: MedVisionAI navy and gold, as a modern dashboard.

Navy sidebar, cool off-white canvas, white rounded cards with soft shadows, a gradient hero banner, one modern
sans-serif (Plus Jakarta Sans) with JetBrains Mono for small labels and numbers.
"""
from __future__ import annotations

import html
import json
from functools import lru_cache

from ..config import ASSETS_DIR, ROOT

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
  border-radius: var(--mv-radius); box-shadow: var(--mv-shadow); padding: 18px 18px 14px; }

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

/* ---------------------------------------------------------------- hero */
.mv-hero { position: relative; overflow: hidden; border-radius: 24px; padding: 30px 34px; margin: 0 0 22px;
  color: #fff; box-shadow: 0 18px 40px rgba(27,34,70,.25);
  background: radial-gradient(900px 300px at 100% -10%, rgba(201,168,106,.38), transparent 60%),
              radial-gradient(600px 300px at -10% 120%, rgba(76,91,212,.45), transparent 60%),
              linear-gradient(135deg, #1B2246 0%, #252E68 55%, #2E3880 100%);
  display: grid; grid-template-columns: 1.45fr 1fr; gap: 28px; align-items: center; }
.mv-hero::after { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .5;
  background-image: radial-gradient(rgba(255,255,255,.07) 1px, transparent 1px); background-size: 18px 18px; }
.mv-hero > * { position: relative; z-index: 1; }
.mv-brandline { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.mv-brandline img { width: 34px; height: 34px; }
.mv-pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: .72rem;
  font-weight: 600; letter-spacing: .02em; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.16);
  color: #E6E8F7; }
.mv-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--mv-gold); box-shadow: 0 0 0 3px rgba(201,168,106,.25); }
.mv-hero h1 { color: #fff !important; font-size: clamp(1.9rem, 4.2vw, 2.9rem) !important; line-height: 1.05 !important;
  margin: 0 !important; padding: 0 !important; }
.mv-hero h1 em { font-style: normal; letter-spacing: -.02em; background: linear-gradient(90deg, #F3DFB3, #C9A86A); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.mv-hero p { color: #C9CDE6; font-size: 1rem; line-height: 1.6; margin: 12px 0 0; max-width: 34rem; }
.mv-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.mv-stat { background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.14); border-radius: 16px; padding: 14px 12px;
  backdrop-filter: blur(6px); }
.mv-stat .n { font-size: 1.55rem; font-weight: 800; color: var(--mv-gold-2); letter-spacing: -.02em; }
.mv-stat .l { font-size: .72rem; color: #B9BEDD; line-height: 1.35; margin-top: 2px; }
@media (max-width: 820px) { .mv-hero { grid-template-columns: 1fr; padding: 24px 22px; } }

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
</style>
"""


@lru_cache(maxsize=None)
def logo_data_uri() -> str:
    import base64

    svg = (ASSETS_DIR / "logo.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


@lru_cache(maxsize=None)
def headline_metrics() -> dict:
    """Key numbers from the saved benchmark report (shown in the hero); empty if the report is missing."""
    try:
        r = json.load(open(ROOT / "reports" / "benchmark_phikon.json", encoding="utf-8"))
        return {"accuracy": r["test_original"]["accuracy_9class"], "tumor_recall": r["test_original"]["tumor_recall"]}
    except Exception:
        return {}


def hero_html() -> str:
    m = headline_metrics()
    stats = []
    if m:
        stats = [(f"{m['accuracy']:.1%}", "accuracy on patients never seen in training"),
                 (f"{m['tumor_recall']:.0%}", "of tumour patches detected (external test)")]
    stats.append(("9", "colorectal tissue types, with calibrated scores"))
    stat_html = "".join(f'<div class="mv-stat"><div class="n">{html.escape(n)}</div><div class="l">{html.escape(l)}</div></div>'
                        for n, l in stats)
    return (
        '<div class="mv-hero"><div>'
        f'<div class="mv-brandline"><img src="{logo_data_uri()}" alt="MedVisionAI"/>'
        '<span class="mv-pill"><span class="dot"></span>Colorectal histopathology · Research prototype</span></div>'
        '<h1>Early detection <em>saves&nbsp;lives.</em></h1>'
        '<p>Upload an H&amp;E image of colorectal tissue for a tissue classification with calibrated confidence, a '
        'tumour finding and a Grad-CAM explanation. A research second opinion, never a diagnosis.</p>'
        f'</div><div class="mv-stats">{stat_html}</div></div>'
    )


def section_html(title: str, note: str = "") -> str:
    return f'<div class="mv-h"><h3>{html.escape(title)}</h3><span>{html.escape(note)}</span></div>'


def chat_hero_html() -> str:
    return (f'<div class="mv-chat-hero"><img src="{logo_data_uri()}" alt=""/>'
            '<h1>How can I help with your case?</h1>'
            '<p>Ask about colorectal pathology, medical imaging or one of your MedVisionAI analyses.</p>'
            '<span class="mv-scope">● Medical and health questions only</span></div>')


def disclaimer_html(text: str) -> str:
    return f'<div class="mv-disclaimer"><b>Research use only.</b> {text}</div>'

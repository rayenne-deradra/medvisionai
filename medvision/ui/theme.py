"""Visual identity from the MedVisionAI pitch deck: a navy / gold sidebar and a warm paper-white main page
with a faint grid, gold accents and serif display type."""
from __future__ import annotations

from functools import lru_cache

from ..config import ASSETS_DIR

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --mv-navy: #1B2246; --mv-paper: #F7F4ED; --mv-card: #FFFFFF; --mv-soft: #FAF8F3;
  --mv-line: rgba(27,34,70,.10); --mv-grid: rgba(27,34,70,.045);
  --mv-gold: #C9A86A; --mv-gold-ink: #9A7536; --mv-ink: #1B2246; --mv-ink-2: #4A5072; --mv-muted: #7C819C;
  --mv-rose: #C2533F; --mv-teal: #2F7F6E;
}
html, body, .stApp, [data-testid="stMarkdownContainer"], button, input, textarea, select {
  font-family: 'DM Sans', system-ui, sans-serif;
}
.stApp {
  background-color: var(--mv-paper);
  background-image: linear-gradient(var(--mv-grid) 1px, transparent 1px),
                    linear-gradient(90deg, var(--mv-grid) 1px, transparent 1px);
  background-size: 56px 56px;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 980px; padding-top: 2.2rem; padding-bottom: 7rem; }
h1, h2, h3 { font-family: 'DM Serif Display', Georgia, serif !important; font-weight: 400 !important; color: var(--mv-ink); }

/* sidebar: navy, as in the pitch deck */
[data-testid="stSidebar"] { background: var(--mv-navy); border-right: 1px solid #2E3768; }
[data-testid="stSidebar"] .stButton > button { justify-content: flex-start; text-align: left; border-radius: 10px; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] { color: var(--mv-navy); font-weight: 600; }
[data-testid="stSidebar"] [data-testid="stExpander"] details { border-color: #2E3768; border-radius: 10px; }
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
[data-testid="stSidebar"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
[data-testid="stSidebar"] [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; }
[data-testid="stSidebar"] [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; }
[data-testid="stSidebar"] .mv-section { color: #8D93B5; }
[data-testid="stSidebar"] .mv-disclaimer { border-color: rgba(201,168,106,.35); background: rgba(201,168,106,.07); color: #D9CCAE; }
[data-testid="stSidebar"] .mv-disclaimer b, [data-testid="stSidebar"] .mv-eyebrow { color: var(--mv-gold); }
[data-testid="stSidebar"] .mv-eyebrow::before { background: var(--mv-gold); }

/* brand block */
.mv-brand { display: flex; align-items: center; gap: 14px; margin: 0 0 6px 0; }
.mv-brand img { width: 46px; height: 46px; }
.mv-eyebrow { font-family: 'JetBrains Mono', monospace; font-size: .72rem; letter-spacing: .22em; color: var(--mv-gold-ink); text-transform: uppercase; }
.mv-eyebrow::before { content: ""; display: inline-block; width: 18px; height: 1px; background: var(--mv-gold-ink); vertical-align: middle; margin-right: 8px; }
.mv-sub { font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .2em; color: var(--mv-muted); text-transform: uppercase; margin-top: 4px; }
.mv-rule { width: 28px; height: 1px; background: var(--mv-gold); margin: 14px 0 6px; }

/* hero */
.mv-hero { display: grid; grid-template-columns: 1fr 1.6fr; gap: 0; align-items: center; margin: 1.2rem 0 1.6rem; }
.mv-hero-left { padding-right: 28px; border-right: 1px solid var(--mv-line); }
.mv-hero-left img { width: 64px; height: 64px; margin-bottom: 16px; }
.mv-hero-right { padding-left: 32px; }
.mv-hero h1 { font-size: clamp(2.2rem, 5vw, 3.4rem); line-height: 1.02; margin: 0; padding: 0; color: var(--mv-ink); }
.mv-hero h1 em { color: var(--mv-gold-ink); font-style: italic; display: block; }
.mv-hero p { color: var(--mv-ink-2); font-size: 1.05rem; line-height: 1.55; margin-top: 14px; max-width: 34rem; }
@media (max-width: 720px) {
  .mv-hero { grid-template-columns: 1fr; }
  .mv-hero-left { border-right: none; border-bottom: 1px solid var(--mv-line); padding: 0 0 18px; }
  .mv-hero-right { padding: 18px 0 0; }
}
@media (max-width: 640px) {   /* two columns on phones instead of Streamlit's one-per-row stacking */
  [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] { flex-direction: row; flex-wrap: wrap; }
  [data-testid="stMainBlockContainer"] [data-testid="stColumn"] { flex: 1 1 calc(50% - 1rem) !important; min-width: calc(50% - 1rem) !important; width: calc(50% - 1rem) !important; }
}
.mv-section { font-family: 'JetBrains Mono', monospace; font-size: .7rem; letter-spacing: .2em; text-transform: uppercase; color: var(--mv-muted); margin: 6px 0 10px; }

/* disclaimer */
.mv-disclaimer { border: 1px solid rgba(154,117,54,.30); background: #FBF5E7; color: #6B5527;
  border-radius: 12px; padding: 10px 14px; font-size: .84rem; line-height: 1.45; }
.mv-disclaimer b { color: var(--mv-gold-ink); }

/* chat */
[data-testid="stChatMessage"] { background: var(--mv-card); border: 1px solid var(--mv-line); border-radius: 16px; padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(27,34,70,.04), 0 6px 18px rgba(27,34,70,.04); }
[data-testid="stChatInput"] textarea { font-size: 1rem; }
[data-testid="stBottomBlockContainer"], [data-testid="stBottom"] > div { background: var(--mv-paper); }

/* report card */
.mv-card { border: 1px solid var(--mv-line); background: var(--mv-soft); border-radius: 14px; padding: 16px 18px; margin: 4px 0 12px; }
.mv-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.mv-card-title { font-family: 'JetBrains Mono', monospace; font-size: .68rem; letter-spacing: .2em; color: var(--mv-muted); text-transform: uppercase; }
.mv-finding { font-family: 'DM Serif Display', Georgia, serif; font-size: 1.9rem; line-height: 1.1; margin-top: 4px; }
.mv-finding.rose { color: var(--mv-rose); } .mv-finding.teal { color: var(--mv-teal); } .mv-finding.muted { color: var(--mv-muted); }
.mv-chip { font-family: 'JetBrains Mono', monospace; font-size: .7rem; letter-spacing: .08em; padding: 5px 10px; border-radius: 999px; border: 1px solid; white-space: nowrap; background: #FFFFFF; }
.mv-chip.High { color: var(--mv-teal); border-color: rgba(47,127,110,.45); }
.mv-chip.Moderate { color: var(--mv-gold-ink); border-color: rgba(154,117,54,.45); }
.mv-chip.Low, .mv-chip.Not { color: var(--mv-rose); border-color: rgba(194,83,63,.45); }
.mv-bar { position: relative; height: 8px; border-radius: 6px; margin: 18px 0 6px;
  background: linear-gradient(90deg, rgba(47,127,110,.55), rgba(201,168,106,.7) 30%, rgba(194,83,63,.75)); }
.mv-bar .thr { position: absolute; top: -6px; width: 2px; height: 20px; background: var(--mv-ink); opacity: .7; }
.mv-bar .dot { position: absolute; top: -5px; width: 18px; height: 18px; margin-left: -9px; border-radius: 50%; background: #FFFFFF; border: 3px solid var(--mv-navy); }
.mv-bar-labels { display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: .64rem; color: var(--mv-muted); }
.mv-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 14px; }
.mv-kv { background: #FFFFFF; border: 1px solid var(--mv-line); border-radius: 10px; padding: 8px 10px; }
.mv-kv .k { font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .14em; color: var(--mv-muted); text-transform: uppercase; }
.mv-kv .v { font-size: .98rem; color: var(--mv-ink); margin-top: 2px; }
.mv-reasons { margin: 12px 0 0; padding-left: 18px; color: var(--mv-ink-2); font-size: .88rem; line-height: 1.5; }
.mv-foot { margin-top: 12px; font-size: .76rem; color: var(--mv-muted); }
.mv-legend { display: flex; align-items: center; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: .64rem; color: var(--mv-muted); margin-top: 4px; }
.mv-legend span.g { flex: 1; height: 6px; border-radius: 4px; background: linear-gradient(90deg, rgba(255,0,0,0) 10%, rgba(255,40,0,.55) 45%, #FFB000 80%, #FFF200); border: 1px solid var(--mv-line); }

/* probability bars */
.mv-prob { display: grid; grid-template-columns: minmax(150px, 1.3fr) 2fr 56px; align-items: center; gap: 10px; padding: 3px 0; font-size: .86rem; color: var(--mv-ink-2); }
.mv-prob .track { height: 8px; background: #ECE6D8; border-radius: 6px; overflow: hidden; }
.mv-prob .fill { display: block; height: 100%; background: #9AA0BD; border-radius: 6px; }
.mv-prob.top .fill { background: var(--mv-navy); }
.mv-prob.top .n { color: var(--mv-ink); font-weight: 600; }
.mv-prob.tumor .fill { background: var(--mv-rose); }
.mv-prob.tumor .n { color: var(--mv-rose); font-weight: 600; }
.mv-prob .p { text-align: right; font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: var(--mv-ink); }
@media (max-width: 520px) { .mv-prob { grid-template-columns: 1fr 1fr 48px; font-size: .78rem; } }
</style>
"""


@lru_cache(maxsize=None)
def logo_data_uri() -> str:
    import base64

    svg = (ASSETS_DIR / "logo.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def brand_html() -> str:
    return (f'<div class="mv-brand"><img src="{logo_data_uri()}" alt="MedVisionAI logo"/>'
            '<div><div class="mv-eyebrow">MedVisionAI</div><div class="mv-sub">Clinical intelligence platform</div>'
            '</div></div>')


def hero_html() -> str:
    return (
        '<div class="mv-hero"><div class="mv-hero-left">'
        f'<img src="{logo_data_uri()}" alt=""/>'
        '<div class="mv-eyebrow">MedVisionAI</div><div class="mv-sub">Clinical intelligence platform</div>'
        '<div class="mv-rule"></div></div>'
        '<div class="mv-hero-right"><h1>Early detection<em>saves lives.</em></h1>'
        '<p>Upload an H&amp;E image of colorectal tissue to get a tissue classification with calibrated confidence '
        'scores, a tumour finding and a Grad-CAM overlay. A research second opinion, never a diagnosis.</p>'
        '</div></div>'
    )


def disclaimer_html(text: str) -> str:
    return f'<div class="mv-disclaimer"><b>Research use only.</b> {text}</div>'

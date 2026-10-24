"""Create an activation code for a paying customer and print the lines to add to Streamlit secrets.

Usage (run on your own computer, never on the server):
    python tools/make_activation_code.py --org "Acme Hospital, Pathology" --expires 2027-10-31 --plan Research

The first run creates ACTIVATION_SECRET in .streamlit/secrets.toml if it is missing. Use the SAME secret on
Streamlit Community Cloud (copy it once into App settings -> Secrets), otherwise no code will match.
The plain code is printed only once: send it to the customer and do not store it anywhere else.
"""
from __future__ import annotations

import argparse
import re
import secrets
import sys
import tomllib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from medvision.auth import code_hash, generate_code  # noqa: E402

SECRETS = ROOT / ".streamlit" / "secrets.toml"


def load_or_create_secret(write: bool) -> str:
    data = tomllib.loads(SECRETS.read_text(encoding="utf-8")) if SECRETS.is_file() else {}
    if data.get("ACTIVATION_SECRET"):
        return data["ACTIVATION_SECRET"]
    value = secrets.token_urlsafe(48)
    if write:
        SECRETS.parent.mkdir(exist_ok=True)
        text = SECRETS.read_text(encoding="utf-8") if SECRETS.is_file() else ""
        # top-level keys must come before any [table] in TOML
        line = f'ACTIVATION_SECRET = "{value}"   # keys activation-code hashes; keep private\n'
        SECRETS.write_text(line + text, encoding="utf-8")
        print(f"Created ACTIVATION_SECRET in {SECRETS}. Copy it to the Streamlit Cloud secrets too.\n")
    return value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", required=True, help="customer organisation name")
    ap.add_argument("--expires", help="last valid day, YYYY-MM-DD (optional)")
    ap.add_argument("--plan", default="Research", help="plan name shown to the customer")
    ap.add_argument("--id", help="short licence label (default: derived from --org)")
    ap.add_argument("--role", choices=["user", "coordinator"], default="user",
                    help="coordinator = hospital staff who triage appointment requests")
    ap.add_argument("--append", action="store_true", help="also append the licence to .streamlit/secrets.toml")
    a = ap.parse_args()
    if a.expires:
        date.fromisoformat(a.expires)             # validates the format
    secret = load_or_create_secret(write=True)
    licence_id = a.id or re.sub(r"[^a-z0-9]+", "-", a.org.lower()).strip("-")[:40] or "licence"
    code = generate_code()
    block = (f"\n[activation_codes.{licence_id}]\n"
             f'hash = "{code_hash(code, secret)}"\n'
             f'organisation = "{a.org}"\n'
             f'plan = "{a.plan}"\n' +
             (f'expires = "{a.expires}"\n' if a.expires else "") +
             (f'role = "{a.role}"\n' if a.role != "user" else "") +
             "active = true\n")
    if a.append:
        with open(SECRETS, "a", encoding="utf-8") as f:
            f.write(block)
    print("Activation code (send this to the customer, it is shown only once):\n")
    print(f"    {code}\n")
    print("Add these lines to Streamlit secrets" + (" (already appended to .streamlit/secrets.toml):" if a.append
                                                   else ":"))
    print(block)


if __name__ == "__main__":
    main()

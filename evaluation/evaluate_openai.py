"""Zero-shot test of a general multimodal model (OpenAI) as a colorectal tissue classifier.

This measures whether a general model could replace the trained classifier. It sends N CRC-VAL-HE-7K images per
class (same sampling as benchmark.py) and asks for one of the 9 tissue types. It costs API credits
(about 9 x N small image requests), so the default is small.

Usage:  python evaluation/evaluate_openai.py --test data/CRC-VAL-HE-7K --per-class 20
Key:    read from .streamlit/secrets.toml (OPENAI_API_KEY) or the environment; never printed.
Writes reports/openai_zero_shot.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PIL import Image  # noqa: E402

from evaluation.benchmark import metrics, robustness_subset  # noqa: E402
from medvision.classifier.foundation import CLASS_NAMES  # noqa: E402
from medvision.llm import ChatMessage, LLMError, OpenAIProvider, QuotaError, pick_model  # noqa: E402

PROMPT = ("This is a 224 x 224 px H&E-stained histology patch of human colorectal tissue (about 0.5 micrometre per "
          "pixel). Classify it as exactly one of these tissue types: " + "; ".join(CLASS_NAMES) +
          ". Answer with JSON only, for example {\"tissue\": \"Mucus\"}.")


def key_from_secrets() -> str | None:
    path = os.path.join(ROOT, ".streamlit", "secrets.toml")
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return tomllib.load(f).get("OPENAI_API_KEY")
    return os.environ.get("OPENAI_API_KEY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True)
    ap.add_argument("--per-class", type=int, default=20)
    ap.add_argument("--model")
    a = ap.parse_args()
    key = key_from_secrets()
    if not key:
        raise SystemExit("No OPENAI_API_KEY in .streamlit/secrets.toml or the environment.")
    probe = OpenAIProvider(key, "")
    model = a.model or pick_model(probe.list_models())
    llm = OpenAIProvider(key, model)
    files, y = robustness_subset(a.test, a.per_class)
    import numpy as np
    probs, scored, failures = [], [], 0
    for i, f in enumerate(files):
        buf = io.BytesIO()
        Image.open(f).convert("RGB").save(buf, "JPEG", quality=92)
        p = np.zeros(len(CLASS_NAMES))
        try:
            reply = "".join(llm.stream("You are a careful histopathology assistant.",
                                       [ChatMessage("user", PROMPT, [buf.getvalue()])]))
            start, end = reply.find("{"), reply.rfind("}")
            answer = json.loads(reply[start:end + 1]).get("tissue", "") if start >= 0 else reply
            match = [k for k, n in enumerate(CLASS_NAMES) if n.lower() in str(answer).lower()]
            if match:
                p[match[0]] = 1
            else:
                failures += 1
        except QuotaError as e:
            raise SystemExit(f"Stopped: {e}")
        except (LLMError, ValueError) as e:
            failures += 1
            print(f"  {os.path.basename(f)}: {str(e)[:80]}", flush=True)
            time.sleep(2)
        if p.any():                       # failed / unparseable requests are reported, not scored as wrong
            probs.append(p)
            scored.append(i)
        if i % 20 == 0:
            print(f"{i + 1}/{len(files)}", flush=True)
    if not scored:
        raise SystemExit("No request succeeded; nothing to score.")
    m = metrics(np.array(probs), y[scored])
    out = {"model": model, "n": len(files), "n_scored": len(scored), "unparseable_or_failed": failures,
           **{k: v for k, v in m.items() if k != "tumor_auroc"}}
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "reports", "openai_zero_shot.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("model", "n", "n_scored", "accuracy_9class", "tumor_recall", "tumor_precision",
                                          "unparseable_or_failed")}, indent=1))


if __name__ == "__main__":
    main()

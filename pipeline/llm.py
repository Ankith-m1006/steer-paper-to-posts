"""Gemini through the AI Studio REST API, asked for JSON. The key is read from an env file and never printed."""
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

MODEL = os.environ.get("STEER_MODEL", "gemini-3.5-flash")
ENV_FILES = [pathlib.Path(__file__).resolve().parents[1] / ".env", pathlib.Path.home() / "graph-hacks" / ".llm.env"]


def _key():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    for f in ENV_FILES:
        if f.exists():
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("GEMINI_API_KEY is not set")


def ask_json(system, prompt, temperature=0.2):
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "x-goog-api-key": _key()})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
            m = re.search(r"[\[{].*[\]}]", text, re.S)
            return json.loads(m.group(0))
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, KeyError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code < 500 and e.code != 429:
                raise
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))

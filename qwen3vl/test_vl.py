#!/usr/bin/env python3
"""
Smoke test for Qwen3-VL-8B-Instruct.

Checks, in order:
  1. /health           — is the server up
  2. /v1/models        — is the served-model-name what we expect
  3. text-only chat    — is generation working at all
  4. image chat        — is the vision path working (a generated PNG, no
                         network fetch, so this works on an air-gapped box)
  5. streaming         — is SSE working end to end

Point it at vLLM directly, or at the LiteLLM proxy:

    python3 test_vl.py                                    # vLLM  :8009
    python3 test_vl.py --base http://localhost:5001 \
                       --key internal-key                 # LiteLLM :5001

Only needs `requests`.
"""

import argparse
import base64
import json
import struct
import sys
import zlib

import requests


# ─── A 64x64 PNG, half red / half blue, built inline ─────────────
# Avoids depending on Pillow or on outbound network access.
def make_test_png(size: int = 64) -> bytes:
    raw = bytearray()
    for y in range(size):
        raw.append(0)                        # PNG per-scanline filter byte
        for x in range(size):
            if x < size // 2:
                raw += bytes((220, 30, 30))  # left half: red
            else:
                raw += bytes((30, 60, 220))  # right half: blue

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw)))
        + chunk(b"IEND", b"")
    )


def data_uri() -> str:
    return "data:image/png;base64," + base64.b64encode(make_test_png()).decode()


# ─── Helpers ─────────────────────────────────────────────────────
PASS, FAIL = "  PASS", "  FAIL"


def post_chat(args, payload, stream=False):
    return requests.post(
        f"{args.base}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {args.key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=args.timeout,
        stream=stream,
    )


# ─── Tests ───────────────────────────────────────────────────────
def test_health(args):
    print("[1] GET /health")
    try:
        r = requests.get(f"{args.base}/health", timeout=10)
    except requests.RequestException as exc:
        print(f"{FAIL} — cannot reach {args.base}: {exc}")
        return False
    ok = r.status_code == 200
    print(f"{PASS if ok else FAIL} — HTTP {r.status_code}")
    return ok


def test_models(args):
    print("[2] GET /v1/models")
    r = requests.get(
        f"{args.base}/v1/models",
        headers={"Authorization": f"Bearer {args.key}"},
        timeout=10,
    )
    if r.status_code != 200:
        print(f"{FAIL} — HTTP {r.status_code}: {r.text[:200]}")
        return False
    ids = [m["id"] for m in r.json().get("data", [])]
    ok = args.model in ids
    print(f"{PASS if ok else FAIL} — served: {ids}")
    if not ok:
        print(f"         expected '{args.model}' — check --served-model-name")
    return ok


def test_text(args):
    print("[3] text-only chat")
    r = post_chat(args, {
        "model": args.model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 16,
        "temperature": 0,
    })
    if r.status_code != 200:
        print(f"{FAIL} — HTTP {r.status_code}: {r.text[:300]}")
        return False
    text = r.json()["choices"][0]["message"]["content"]
    print(f"{PASS} — {text.strip()!r}")
    return True


def test_vision(args):
    print("[4] image chat  (64x64 PNG: left half red, right half blue)")
    r = post_chat(args, {
        "model": args.model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri()}},
                {"type": "text",
                 "text": "What two colors are in this image, and which side is each on?"},
            ],
        }],
        "max_tokens": 100,
        "temperature": 0,
    })
    if r.status_code != 200:
        print(f"{FAIL} — HTTP {r.status_code}: {r.text[:400]}")
        print("         400 with an unknown-content-part error usually means")
        print("         model_info.supports_vision is missing in the LiteLLM config.")
        return False

    text = r.json()["choices"][0]["message"]["content"]
    print(f"         reply: {text.strip()[:200]}")
    lowered = text.lower()
    saw_colors = "red" in lowered and "blue" in lowered
    print(f"{PASS if saw_colors else FAIL} — "
          f"{'named both colors' if saw_colors else 'did not name both colors — vision path suspect'}")
    return saw_colors


def test_stream(args):
    print("[5] streaming")
    r = post_chat(args, {
        "model": args.model,
        "messages": [{"role": "user", "content": "Count from 1 to 5."}],
        "max_tokens": 60,
        "temperature": 0,
        "stream": True,
    }, stream=True)

    if r.status_code != 200:
        print(f"{FAIL} — HTTP {r.status_code}: {r.text[:300]}")
        return False

    chunks = 0
    for line in r.iter_lines():
        if not line or not line.startswith(b"data: "):
            continue
        body = line[6:]
        if body == b"[DONE]":
            break
        try:
            json.loads(body)
            chunks += 1
        except json.JSONDecodeError:
            pass

    ok = chunks > 0
    print(f"{PASS if ok else FAIL} — {chunks} SSE chunks")
    return ok


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base",  default="http://localhost:8009",
                   help="vLLM (8009) or LiteLLM proxy (5001)")
    p.add_argument("--key",   default="not-needed",
                   help="'not-needed' for vLLM, master_key for LiteLLM")
    p.add_argument("--model", default="qwen3vl8b")
    p.add_argument("--timeout", type=int, default=300)
    args = p.parse_args()

    print(f"Target: {args.base}  model={args.model}\n")

    if not test_health(args):
        print("\nServer not reachable — nothing else can run.")
        sys.exit(1)

    results = [
        test_models(args),
        test_text(args),
        test_vision(args),
        test_stream(args),
    ]

    passed = sum(results) + 1          # +1 for health
    total = len(results) + 1
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

"""Minimal Presidio REST server for LiteLLM guardrails.

Serves BOTH /analyze and /anonymize on a single port, so you point both
LiteLLM env vars at the same base URL. No Docker, no repo clone required --
just the pip packages below.

Setup (all user-space, no sudo):
    pip install presidio-analyzer presidio-anonymizer flask
    python -m spacy download en_core_web_lg

Run (pick any free port > 1024):
    PORT=5003 python presidio_server.py
    # or in the background:
    # nohup env PORT=5003 python presidio_server.py > ~/presidio.log 2>&1 &

Point LiteLLM at it (both vars -> same server) before launching the proxy:
    export PRESIDIO_ANALYZER_API_BASE="http://localhost:5003"
    export PRESIDIO_ANONYMIZER_API_BASE="http://localhost:5003"
"""
import os

from flask import Flask, Response, jsonify, request
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig, RecognizerResult

app = Flask(__name__)

# Engines load once at startup. The analyzer pulls in the spaCy model, so the
# first boot is slow (and will error here if en_core_web_lg isn't installed).
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


@app.get("/health")
def health():
    return "ok"


@app.post("/analyze")
def analyze():
    data = request.get_json(force=True)
    text = data.get("text")
    if not text:
        return jsonify(error="No text provided"), 400
    results = analyzer.analyze(
        text=text,
        language=data.get("language", "en"),
        score_threshold=data.get("score_threshold"),
        entities=data.get("entities"),
    )
    # LiteLLM reads entity_type / start / end / score from each item.
    return jsonify([r.to_dict() for r in results])


@app.post("/anonymize")
def anonymize():
    data = request.get_json(force=True)
    text = data.get("text", "")

    analyzer_results = [
        RecognizerResult(r["entity_type"], r["start"], r["end"], r["score"])
        for r in data.get("analyzer_results", [])
    ]

    operators = None
    requested = data.get("anonymizers")
    if requested:
        operators = {}
        for entity, cfg in requested.items():
            op_name = cfg.get("type", "replace")
            params = {k: v for k, v in cfg.items() if k != "type"}
            operators[entity] = OperatorConfig(op_name, params)

    result = anonymizer.anonymize(
        text=text, analyzer_results=analyzer_results, operators=operators
    )
    # EngineResult.to_json() -> {"text": "...", "items": [...]}; LiteLLM uses "text".
    return Response(result.to_json(), content_type="application/json")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5003"))
    app.run(host="0.0.0.0", port=port)

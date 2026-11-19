"""
GradeX - Student Performance Predictor (University of Zimbabwe, Project 19)
Run:  python app.py      then open  http://127.0.0.1:5000
"""
import json
import os
import re
import threading
from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Flask, abort, jsonify, render_template, request, send_file

import config
import ml

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # uploads up to 2 MB
MESSAGES = ml.DATA_DIR.parent / "messages.jsonl"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.get("/")
def index():
    boot = {
        "programmes": ml.list_programmes(),
        "grading": [{"min": lo, "short": s, "label": l, "colour": c} for lo, s, l, c in config.GRADING],
        "pass": config.PASS_MARK,
    }
    return render_template("index.html", cfg=config, fields=ml.FIELDS, selects=ml.SELECTS,
                           boot=boot, required=ml.REQUIRED)


def _slug_or_404(slug: str) -> str:
    if not ml.SLUG_RE.match(slug) or not (ml.DATA_DIR / f"{slug}.csv").exists():
        abort(404)
    return slug


@app.get("/api/summary/<slug>")
def summary(slug):
    return jsonify(ml.get_bundle(_slug_or_404(slug))["summary"])


@app.post("/api/predict/<slug>")
def predict(slug):
    return jsonify(ml.predict(_slug_or_404(slug), request.get_json(silent=True) or {}))


@app.get("/api/download/<slug>.csv")
def download(slug):
    return send_file(ml.DATA_DIR / f"{_slug_or_404(slug)}.csv", as_attachment=True,
                     download_name=f"{slug}.csv", mimetype="text/csv")


@app.get("/api/template.csv")
def template():
    ml.ensure_builtin()
    df = pd.read_csv(ml.DATA_DIR / "computer_science.csv").head(8)
    buf = BytesIO(df.to_csv(index=False).encode("utf-8"))
    return send_file(buf, as_attachment=True, download_name="gradex_template.csv", mimetype="text/csv")


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    name = request.form.get("name", "").strip()
    if not f or not f.filename.lower().endswith(".csv"):
        return jsonify(error="Please choose a .csv file."), 400
    if not re.fullmatch(r"[A-Za-z0-9 _-]{2,40}", name):
        return jsonify(error="Programme name: 2-40 letters, numbers or spaces."), 400
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not ml.SLUG_RE.match(slug):
        return jsonify(error="Please use a different programme name."), 400
    try:
        df = ml.validate_frame(pd.read_csv(f))
    except Exception as exc:  # unreadable file, missing columns, too few rows
        return jsonify(error=str(exc)[:220]), 400
    df.to_csv(ml.DATA_DIR / f"{slug}.csv", index=False)
    return jsonify(ok=True, slug=slug, programmes=ml.list_programmes())


@app.post("/api/contact")
def contact():
    d = request.get_json(silent=True) or {}
    name = str(d.get("name", "")).strip()[:80]
    email = str(d.get("email", "")).strip()[:120]
    subject = str(d.get("subject", "")).strip()[:120]
    message = str(d.get("message", "")).strip()[:2000]
    if not name or not EMAIL_RE.match(email) or len(message) < 5:
        return jsonify(error="Please enter your name, a valid email and a message."), 400
    with open(MESSAGES, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"), "name": name,
                             "email": email, "subject": subject, "message": message},
                            ensure_ascii=False) + "\n")
    return jsonify(ok=True)


if __name__ == "__main__":
    ml.ensure_builtin()
    threading.Thread(target=ml.warm, daemon=True).start()  # train models in the background
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  GradeX is running -> http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)

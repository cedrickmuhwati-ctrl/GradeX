"""
ml.py - data, models and evaluation for GradeX.

* Generates schema-based SYNTHETIC University of Zimbabwe datasets
  (200 students each for Computer Science, Law and Medicine).
* Trains and compares: Mean baseline, Linear Regression, Decision Tree, Random Forest.
* Evaluates with 5-fold cross-validation (fixed, so results are repeatable).
* Ranks features with permutation importance.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

import config

DATA_DIR = Path(__file__).parent / "data"
TARGET = "final_mark"
SEED = 42
N_STUDENTS = 200

LEVELS = [f"Level {x}" for x in ("1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2")]
HOUSING = ["On campus", "Off campus", "Home"]
FUNDING = ["Self-funded", "Family-sponsored", "Scholarship"]
INTERNET = ["Reliable", "Limited"]

# Numeric predictors, with the slider settings used by the website form.
FIELDS = [
    {"key": "attendance", "label": "Lecture attendance", "unit": "%", "min": 0, "max": 100, "step": 1, "default": 75, "group": "Attendance"},
    {"key": "coursework", "label": "Coursework mark", "unit": "%", "min": 0, "max": 100, "step": 1, "default": 60, "group": "Coursework"},
    {"key": "prev_avg", "label": "Previous semester average", "unit": "%", "min": 0, "max": 100, "step": 1, "default": 58, "group": "Coursework"},
    {"key": "study_hours", "label": "Study hours per week", "unit": "h", "min": 0, "max": 40, "step": 1, "default": 12, "group": "Study habits"},
    {"key": "part_time_hours", "label": "Part-time work per week", "unit": "h", "min": 0, "max": 30, "step": 1, "default": 3, "group": "Study habits"},
    {"key": "a_level_points", "label": "A-Level points", "unit": "pts", "min": 3, "max": 15, "step": 1, "default": 10, "group": "Background"},
]
SELECTS = [
    {"key": "level", "label": "Level of study", "options": LEVELS, "default": "Level 2.1"},
    {"key": "housing", "label": "Accommodation", "options": HOUSING, "default": "Off campus"},
    {"key": "funding", "label": "Fees funding", "options": FUNDING, "default": "Self-funded"},
    {"key": "internet", "label": "Internet access", "options": INTERNET, "default": "Reliable"},
]
NUM = [f["key"] for f in FIELDS]
CAT = [s["key"] for s in SELECTS]
FEATURES = NUM + CAT
REQUIRED = FEATURES + [TARGET]
LABELS = {f["key"]: f["label"] for f in FIELDS}
LABELS.update({s["key"]: s["label"] for s in SELECTS})
LABELS[TARGET] = "Final mark"

PROFILES = {  # synthetic-data settings per programme
    "computer_science": {"title": "Computer Science", "base": 60, "a_range": (8, 15), "seed": 101},
    "law": {"title": "Law", "base": 57, "a_range": (9, 15), "seed": 202},
    "medicine": {"title": "Medicine", "base": 63, "a_range": (12, 15), "seed": 303},
}
SLUG_RE = re.compile(r"^[a-z0-9_]{2,40}$")


# --------------------------------------------------------------------------- #
# Grading helpers
# --------------------------------------------------------------------------- #
def classify(mark: float) -> dict:
    for lo, short, long, colour in config.GRADING:
        if mark >= lo:
            return {"short": short, "label": long, "colour": colour}
    lo, short, long, colour = config.GRADING[-1]
    return {"short": short, "label": long, "colour": colour}


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def generate(slug: str, n: int = N_STUDENTS) -> pd.DataFrame:
    p = PROFILES[slug]
    r = np.random.default_rng(p["seed"])
    ability = r.normal(0, 1, n)
    lo, hi = p["a_range"]
    frac = np.clip(0.55 + 0.2 * ability + r.normal(0, 0.15, n), 0, 1)
    a_level = np.round(lo + (hi - lo) * frac)
    attendance = np.clip(np.round(r.normal(76 + 6 * ability, 11, n)), 30, 100)
    study = np.clip(np.round(r.normal(11 + 2.5 * ability, 4, n)), 1, 40)
    part_time = np.clip(np.round(r.gamma(1.6, 2.8, n)), 0, 30)
    housing = r.choice(HOUSING, n, p=[0.35, 0.45, 0.20])
    funding = r.choice(FUNDING, n, p=[0.50, 0.30, 0.20])
    internet = r.choice(INTERNET, n, p=[0.60, 0.40])
    level = r.choice(LEVELS, n)
    prev = np.clip(np.round(p["base"] - 2 + 9 * ability + 0.6 * (a_level - a_level.mean()) + r.normal(0, 5, n)), 20, 95)
    cw = np.clip(np.round(p["base"] + 8 * ability + 0.1 * (attendance - 75) + 0.3 * (study - 11) + r.normal(0, 6, n)), 15, 98)

    final = (8 + 0.32 * cw + 0.16 * prev + 0.22 * attendance + 0.50 * np.minimum(study, 22)
             - 0.15 * part_time - 0.40 * np.maximum(0, 60 - attendance)
             - 2.5 * (internet == "Limited") - 1.0 * (housing == "Off campus")
             + 1.5 * (funding == "Scholarship") + 4.0 * ((cw > 70) & (attendance > 85))
             + r.normal(0, 4.0, n))
    final = np.clip(np.round(final), 5, 98)

    df = pd.DataFrame({
        "attendance": attendance, "coursework": cw, "prev_avg": prev, "study_hours": study,
        "part_time_hours": part_time, "a_level_points": a_level,
        "level": level, "housing": housing, "funding": funding, "internet": internet,
        TARGET: final,
    })
    for c in NUM + [TARGET]:
        df[c] = df[c].astype(int)
    return df[REQUIRED]


def validate_frame(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing column(s): " + ", ".join(missing))
    df = df[REQUIRED].copy()
    for c in NUM + [TARGET]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna()
    if len(df) < 30:
        raise ValueError("The file needs at least 30 valid student rows.")
    df[TARGET] = df[TARGET].clip(0, 100)
    for c in CAT:
        df[c] = df[c].astype(str).str.strip()
    return df.reset_index(drop=True)


def ensure_builtin() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for slug in PROFILES:
        path = DATA_DIR / f"{slug}.csv"
        if not path.exists():
            generate(slug).to_csv(path, index=False)


def title_of(slug: str) -> str:
    return PROFILES[slug]["title"] if slug in PROFILES else slug.replace("_", " ").title()


def list_programmes() -> list[dict]:
    ensure_builtin()
    found = [p.stem for p in DATA_DIR.glob("*.csv") if SLUG_RE.match(p.stem)]
    order = [s for s in PROFILES if s in found] + sorted(s for s in found if s not in PROFILES)
    out = []
    for s in order:
        with open(DATA_DIR / f"{s}.csv", encoding="utf-8") as fh:
            n = max(sum(1 for _ in fh) - 1, 0)
        out.append({"slug": s, "title": title_of(s), "n": n})
    return out


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
def _make_models() -> dict[str, Pipeline]:
    def prep(scale: bool) -> ColumnTransformer:
        return ColumnTransformer([
            ("num", StandardScaler() if scale else "passthrough", NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ])
    return {
        "Mean baseline": Pipeline([("prep", prep(False)), ("model", DummyRegressor())]),
        "Linear Regression": Pipeline([("prep", prep(True)), ("model", LinearRegression())]),
        "Decision Tree": Pipeline([("prep", prep(False)),
                                   ("model", DecisionTreeRegressor(max_depth=5, min_samples_leaf=8, random_state=SEED))]),
        "Random Forest": Pipeline([("prep", prep(False)),
                                   ("model", RandomForestRegressor(n_estimators=200, min_samples_leaf=2,
                                                                   random_state=SEED, n_jobs=1))]),
    }


def _train(slug: str, df: pd.DataFrame) -> dict:
    X, y = df[FEATURES], df[TARGET].values
    cv = KFold(5, shuffle=True, random_state=SEED)
    passmark = config.PASS_MARK

    rows = []
    for name, model in _make_models().items():
        pred = np.clip(cross_val_predict(model, X, y, cv=cv), 0, 100)
        rows.append({
            "model": name,
            "mae": round(float(mean_absolute_error(y, pred)), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(y, pred))), 2),
            "r2": round(float(r2_score(y, pred)), 3),
            "pass_acc": round(float(((pred >= passmark) == (y >= passmark)).mean() * 100), 1),
        })
    real = [r for r in rows if r["model"] != "Mean baseline"]
    best = min(real, key=lambda r: r["mae"])
    fitted = {n: m.fit(X, y) for n, m in _make_models().items()}

    # Feature selection: permutation importance of the raw columns (Random Forest, hold-out split)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=SEED)
    rf = _make_models()["Random Forest"].fit(Xtr, ytr)
    pi = permutation_importance(rf, Xte, yte, n_repeats=15, random_state=SEED,
                                scoring="neg_mean_absolute_error", n_jobs=1)
    imp = np.clip(pi.importances_mean, 0, None)
    share = imp / imp.sum() * 100 if imp.sum() > 0 else imp
    importance = sorted(({"key": c, "label": LABELS[c], "share": round(float(s), 1)}
                         for c, s in zip(FEATURES, share)), key=lambda d: -d["share"])

    # The three basics from the project brief: attendance, coursework, study habits
    passed = df[TARGET] >= passmark
    basics, relations = [], {}
    for key, name, icon in (("attendance", "Attendance", "bi-calendar-check"),
                            ("coursework", "Coursework", "bi-journal-check"),
                            ("study_hours", "Study habits", "bi-alarm")):
        r = float(np.corrcoef(df[key], df[TARGET])[0, 1])
        basics.append({"key": key, "name": name, "icon": icon, "r": round(r, 2),
                       "pass_mean": round(float(df.loc[passed, key].mean()), 1) if passed.any() else None,
                       "fail_mean": round(float(df.loc[~passed, key].mean()), 1) if (~passed).any() else None,
                       "unit": "%" if key != "study_hours" else " h/week"})
        slope, icpt = np.polyfit(df[key], df[TARGET], 1)
        x0, x1 = float(df[key].min()), float(df[key].max())
        relations[key] = {"label": LABELS[key],
                          "points": [{"x": int(a), "y": int(b)} for a, b in zip(df[key], df[TARGET])],
                          "line": [{"x": x0, "y": round(float(slope * x0 + icpt), 1)},
                                   {"x": x1, "y": round(float(slope * x1 + icpt), 1)}]}

    # Class distribution (Zimbabwean grading scale)
    dist, upper = [], 100
    for lo, short, long, colour in config.GRADING:
        count = int(((df[TARGET] >= lo) & (df[TARGET] <= upper)).sum())
        dist.append({"short": short, "range": f"{lo}-{upper}%", "count": count, "colour": colour})
        upper = lo - 1
    dist.reverse()

    counters = {
        "students": int(len(df)),
        "avg": round(float(df[TARGET].mean()), 1),
        "min": int(df[TARGET].min()),
        "pass": round(float(passed.mean() * 100)),
        "attendance": round(float(df["attendance"].mean())),
        "accuracy": round(best["r2"] * 100),
    }
    top = importance[:2]
    insights = {
        "models": f"{best['model']} predicts best: on average its estimate is {best['mae']:.1f} marks away from the "
                  f"real mark, and it correctly separates pass from fail {best['pass_acc']:.0f}% of the time.",
        "importance": f"{top[0]['label']} and {top[1]['label'].lower()} have the biggest influence on the final mark.",
        "dist": f"{counters['pass']}% of students reach the {passmark}% pass mark; "
                f"{dist[-1]['count']} reach Class 1.",
    }
    b0 = basics[0]
    insights["scatter"] = (f"Students who passed attended {b0['pass_mean']:.0f}% of lectures on average, "
                           f"compared with {b0['fail_mean']:.0f}% for those who failed." if b0["fail_mean"] is not None
                           else "Each dot is one student; the line shows the overall trend.")

    summary = {
        "slug": slug, "title": title_of(slug), "counters": counters, "distribution": dist,
        "models": rows, "best": best["model"], "importance": importance[:8], "basics": basics,
        "relations": relations, "insights": insights,
        "rows": json.loads(df.to_json(orient="records")),
    }
    return {"summary": summary, "fitted": fitted, "best": best["model"], "df": df}


_LOCK = threading.Lock()
_CACHE: dict = {}


def get_bundle(slug: str) -> dict:
    if not SLUG_RE.match(slug):
        raise FileNotFoundError(slug)
    ensure_builtin()
    path = DATA_DIR / f"{slug}.csv"
    if not path.exists():
        raise FileNotFoundError(slug)
    key = path.stat().st_mtime_ns
    with _LOCK:
        hit = _CACHE.get(slug)
        if hit and hit[0] == key:
            return hit[1]
        bundle = _train(slug, validate_frame(pd.read_csv(path)))
        _CACHE[slug] = (key, bundle)
        return bundle


def warm() -> None:
    for p in list_programmes():
        try:
            get_bundle(p["slug"])
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Prediction
# --------------------------------------------------------------------------- #
def predict(slug: str, values: dict) -> dict:
    b = get_bundle(slug)
    row = {}
    for f in FIELDS:
        try:
            v = float(values.get(f["key"], f["default"]))
        except (TypeError, ValueError):
            v = f["default"]
        row[f["key"]] = min(max(v, f["min"]), f["max"])
    for s in SELECTS:
        v = str(values.get(s["key"], s["default"]))
        row[s["key"]] = v if v in s["options"] else s["default"]
    X = pd.DataFrame([row])[FEATURES]

    def run(model_name: str, frame: pd.DataFrame) -> float:
        return float(np.clip(b["fitted"][model_name].predict(frame)[0], 0, 100))

    preds = {n: round(run(n, X), 1) for n in ("Linear Regression", "Decision Tree", "Random Forest")}
    best = b["best"]
    mark = preds[best]
    cls = classify(mark)

    scenarios = [("Attend at least 90% of lectures", "attendance", max(row["attendance"], 90)),
                 ("Study 5 more hours a week", "study_hours", min(40, row["study_hours"] + 5)),
                 ("Raise coursework by 10 marks", "coursework", min(100, row["coursework"] + 10)),
                 ("Cut part-time work to 0 hours", "part_time_hours", 0)]
    tips = []
    for text, key, new in scenarios:
        if new == row[key]:
            continue
        alt = X.copy()
        alt[key] = new
        gain = run(best, alt) - mark
        if gain >= 0.5:
            tips.append({"text": text, "gain": round(gain, 1)})
    tips.sort(key=lambda t: -t["gain"])

    return {"mark": mark, "best": best, "class": cls, "passed": mark >= config.PASS_MARK,
            "models": preds, "tips": tips[:3]}

# GradeX · Student Performance Predictor
University of Zimbabwe · Introduction to AI & Expert Systems · Group Project 19

A Flask website that predicts a student's final mark (0-100%) from **attendance, coursework and study habits**
(plus A-Level points, accommodation, fees funding and internet access) and compares
**Linear Regression, Decision Tree and Random Forest** against a "guess the average" baseline.

## Run it (Windows)
```
cd path\to\gradex
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 . Keep the terminal open. (If `python` is not found, try `py app.py`.)
The first start takes about 10-15 seconds while the models train; after that everything is instant.
Fonts load from Google Fonts when online; the site still works offline with a system font.

## Where to change things
| What | File |
|---|---|
| Site name, grading scale, pass mark, your details, team, references | `config.py` |
| Datasets (200 students each) | `data/*.csv` (auto-created on first run) |
| Models, evaluation, feature selection | `ml.py` |
| Web routes (API) | `app.py` |
| Page layout and text | `templates/index.html` |
| Colours and styling | `static/css/style.css` |
| Charts, counters, predictor logic | `static/js/app.js` |

## Add a dataset
Use the "Add a programme" box on the site, or save a CSV in `data/` (e.g. `engineering.csv`).
Required columns: attendance, coursework, prev_avg, study_hours, part_time_hours, a_level_points,
level, housing, funding, internet, final_mark. Download the template from the site.
To regenerate the built-in data, delete the CSV files in `data/` and restart.

## Methodology (for the report)
1. **Data:** synthetic, based on the University of Zimbabwe context (no public Zimbabwean student dataset exists). Labelled as such on the site.
2. **Pre-processing:** numeric columns scaled, categories one-hot encoded, inside a scikit-learn Pipeline (no data leakage).
3. **Feature selection:** permutation importance (Random Forest, hold-out split).
4. **Models:** Mean baseline, Linear Regression, Decision Tree (depth 5), Random Forest (200 trees).
5. **Evaluation:** 5-fold cross-validation (fixed seed 42): average error (MAE), RMSE, R², pass/fail accuracy.
6. **Grading:** Class 1 >= 75, 2.1 65-74, 2.2 60-64, 3 50-59, Fail < 50 (edit in `config.py` to match your faculty).

## Limitations
Synthetic data, so accuracy figures describe the generator, not real students. Predictions show correlation,
not causation, and must not be used to make decisions about real people.

Contact: Cedrick A S Muhwati · cedrickmuhwati@gmail.com

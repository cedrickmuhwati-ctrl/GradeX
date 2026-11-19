"""
config.py - everything you may want to edit WITHOUT touching the code:
site name, grading scale, creator and team details, references.
"""

SITE_NAME = "GradeX"
TAGLINE = "Student Performance Predictor"
UNIVERSITY = "University of Zimbabwe"
COURSE = "Introduction to AI & Expert Systems · Group Project 19"
LOCATION = "University of Zimbabwe, Mount Pleasant, Harare, Zimbabwe"

# ---- Grading scale (percentage marks) ---------------------------------------
# Each row: (lowest mark in the class, short label, long label, colour).
# Keep the rows ordered from highest to lowest. Adjust if your faculty differs.
PASS_MARK = 50
GRADING = [
    (75, "1",    "Class 1 · Distinction",   "#6366f1"),
    (65, "2.1",  "Class 2.1 · Upper second", "#22d3ee"),
    (60, "2.2",  "Class 2.2 · Lower second", "#84cc16"),
    (50, "3",    "Class 3 · Pass",           "#f59e0b"),
    (0,  "Fail", "Fail",                     "#ef4444"),
]

# ---- Site creator -------------------------------------------------------------
CREATOR = {
    "name": "Cedrick A S Muhwati",
    "programme": "BSc Computer Science",
    "level": "Level 2.1",
    "email": "cedrickmuhwati@gmail.com",
    "phone": "0784109800",
}

# ---- Group members (as supplied - please double-check spelling and numbers) ---
TEAM = [
    {"name": "Cedrick A S Muhwati",  "reg": "R2528756 HCS ",   "role": "Developer"},
    {"name": "Tanyaradzwa Nyakunuwa","reg": "R24200347 HCC",   "role": "Data and testing"},
    {"name": "Nokutenda Hamandishe", "reg": "R242027 9 HAI",   "role": "Developer"},
    {"name": "Caitlyn Nyabeze",      "reg": "R252871 HCS",     "role": "Presenter"},
    {"name": "Tashinga Mandenga",    "reg": "R25286642 HCC",   "role": "Documentation"},
    {"name": "Anotida Chimanga",     "reg": "R252827  HAI",    "role": "Project lead"},
]

# ---- References ---------------------------------------------------------------
REFERENCES = [
    {"text": "P. Cortez and A. Silva (2008). Using Data Mining to Predict Secondary School "
             "Student Performance. Proceedings of FUBUTEC 2008, pp. 5-12.",
     "url": "https://archive.ics.uci.edu/dataset/320/student+performance"},
    {"text": "F. Pedregosa et al. (2011). Scikit-learn: Machine Learning in Python. "
             "Journal of Machine Learning Research 12, 2825-2830.",
     "url": "https://scikit-learn.org"},
    {"text": "L. Breiman (2001). Random Forests. Machine Learning 45(1), 5-32.", "url": ""},
    {"text": "Flask (web framework) and Chart.js (charts) - open-source tools.",
     "url": "https://flask.palletsprojects.com"},
]

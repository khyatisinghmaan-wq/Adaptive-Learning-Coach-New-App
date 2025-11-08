from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, datetime
from utils.privacy import purge_old_events, can_show_aggregate
from utils.rag_engine import load_kb, simple_retrieve

APP_SECRET = os.environ.get("APP_SECRET", "dev-secret")  # replace in production
DB_PATH = os.path.join("data", "alc.db")
KB_DIR = os.path.join("data", "kb")

app = Flask(__name__)
app.secret_key = APP_SECRET

# ---------------------
# DB helpers
# ---------------------
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alias TEXT UNIQUE,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS survey_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_alias TEXT,
        q1 INTEGER, q2 INTEGER, q3 INTEGER,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS lesson_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_alias TEXT,
        lesson_id INTEGER,
        completed INTEGER,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_alias TEXT,
        query TEXT,
        answer TEXT,
        created_at TEXT
    )""")
    con.commit()
    con.close()

def seed_data():
    con = get_db()
    cur = con.cursor()
    # Seed lessons if empty
    cur.execute("SELECT COUNT(*) FROM lessons")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO lessons(title) VALUES(?)", [
            ("ALC Overview",),
            ("Motivation Basics",),
            ("Applying Micro-Lessons",),
        ])

    # Seed demo users & survey responses for n >= 5
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] < 5:
        aliases = [f"user0{i}" for i in range(1,6)]
        now = datetime.datetime.utcnow().isoformat()
        for a in aliases:
            try:
                cur.execute("INSERT OR IGNORE INTO users(alias, created_at) VALUES(?, ?)", (a, now))
                cur.execute("INSERT INTO survey_responses(user_alias, q1, q2, q3, created_at) VALUES(?,?,?,?,?)",
                            (a, 4, 4, 4, now))
                # one lesson completion each
                cur.execute("INSERT INTO lesson_events(user_alias, lesson_id, completed, created_at) VALUES(?,?,?,?)",
                            (a, 1, 1, now))
            except Exception:
                pass
    con.commit()
    con.close()

# Initialize DB and retention
os.makedirs("data", exist_ok=True)
init_db()
purge_old_events(DB_PATH)
seed_data()

# Load KB once
KB_DOCS = load_kb(KB_DIR)

# ---------------------
# Routes
# ---------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        alias = request.form.get("alias","").strip()
        if alias:
            session["alias"] = alias
            # ensure user row
            con = get_db(); cur = con.cursor()
            cur.execute("INSERT OR IGNORE INTO users(alias, created_at) VALUES(?,?)",
                        (alias, datetime.datetime.utcnow().isoformat()))
            con.commit(); con.close()
            flash(f"Logged in as {alias}")
            return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/chat", methods=["GET","POST"])
def chat():
    answer = None
    if request.method == "POST":
        q = request.form.get("query","")
        ans = simple_retrieve(q, KB_DOCS)
        answer = ans
        # log
        alias = session.get("alias","anon")
        con = get_db(); cur = con.cursor()
        cur.execute("INSERT INTO chat_logs(user_alias, query, answer, created_at) VALUES(?,?,?,?)",
                    (alias, q, ans, datetime.datetime.utcnow().isoformat()))
        con.commit(); con.close()
    return render_template("chat.html", answer=answer)

@app.route("/survey", methods=["GET","POST"])
def survey():
    if request.method == "POST":
        alias = session.get("alias","anon")
        q1 = int(request.form.get("q1",3))
        q2 = int(request.form.get("q2",3))
        q3 = int(request.form.get("q3",3))
        con = get_db(); cur = con.cursor()
        cur.execute("INSERT INTO survey_responses(user_alias, q1, q2, q3, created_at) VALUES(?,?,?,?,?)",
                    (alias, q1, q2, q3, datetime.datetime.utcnow().isoformat()))
        con.commit(); con.close()
        flash("Thanks for your response!")
        return redirect(url_for("survey"))
    return render_template("survey.html")

@app.route("/lessons", methods=["GET","POST"])
def lessons():
    con = get_db(); cur = con.cursor()
    if request.method == "POST":
        alias = session.get("alias","anon")
        lesson_id = int(request.form.get("lesson_id"))
        # Toggle completion by inserting an event with completed flag 1/0 (flip last state)
        cur.execute("SELECT completed FROM lesson_events WHERE user_alias=? AND lesson_id=? ORDER BY id DESC LIMIT 1",
                    (alias, lesson_id))
        row = cur.fetchone()
        new_state = 0 if (row and row["completed"]==1) else 1
        cur.execute("INSERT INTO lesson_events(user_alias, lesson_id, completed, created_at) VALUES(?,?,?,?)",
                    (alias, lesson_id, new_state, datetime.datetime.utcnow().isoformat()))
        con.commit()
    # Build simple view: last state per lesson for this user
    cur.execute("SELECT id, title FROM lessons")
    lessons = [{"id": r["id"], "title": r["title"], "completed": False} for r in cur.fetchall()]
    alias = session.get("alias","anon")
    for L in lessons:
        cur.execute("SELECT completed FROM lesson_events WHERE user_alias=? AND lesson_id=? ORDER BY id DESC LIMIT 1",
                    (alias, L["id"]))
        row = cur.fetchone()
        L["completed"] = bool(row["completed"]) if row else False
    con.close()
    return render_template("lessons.html", lessons=lessons)

@app.route("/metrics")
def metrics():
    con = get_db(); cur = con.cursor()
    cur.execute("SELECT q1, q2, q3 FROM survey_responses")
    rows = cur.fetchall()
    n = len(rows)
    can_show = can_show_aggregate(n)
    q1_mean = sum(r["q1"] for r in rows)/n if n else 0
    q2_mean = sum(r["q2"] for r in rows)/n if n else 0
    q3_mean = sum(r["q3"] for r in rows)/n if n else 0
    # lesson completions in last 90 days
    cur.execute("SELECT COUNT(*) as c FROM lesson_events WHERE completed=1")
    total_completions = cur.fetchone()["c"]
    con.close()
    return render_template("metrics.html",
                           can_show=can_show, n=n,
                           q1_mean=q1_mean, q2_mean=q2_mean, q3_mean=q3_mean,
                           total_completions=total_completions)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

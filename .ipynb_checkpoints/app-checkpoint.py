from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
app = Flask(__name__)
app.secret_key = "change_me_to_a_long_random_secret"  # поменяй на длинный рандом
# ---------- DB ----------
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS onboarding_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_key TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_key),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()
    
_db_inited = False

@app.before_request
def ensure_db():
    global _db_inited
    if not _db_inited:
        init_db()
        _db_inited = True
# ---------- Pages ----------
@app.route("/")
def home():
    # welcome page
    return render_template("index.html")


# ---------- Auth ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not nickname or not email or not password:
            flash("Fill all fields.")
            return redirect(url_for("signup"))

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)",
                (nickname, email, generate_password_hash(password)),
            )
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            flash("Email already exists.")
            return redirect(url_for("signup"))

        conn.close()

        session["user_id"] = user_id
        session["nickname"] = nickname
        return redirect(url_for("onboarding_intro"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()

        if not login_value or not password:
            flash("Fill all fields.")
            return redirect(url_for("login"))

        conn = get_db()
        cur = conn.cursor()

        # login_value 
        cur.execute(
            "SELECT * FROM users WHERE lower(email)=lower(?) OR nickname=?",
            (login_value, login_value),
        )
        user = cur.fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid nickname/email or password.")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["nickname"] = user["nickname"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- Dashboard ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return f"Hello, {session.get('nickname','User')}! Dashboard here."


# ---------- Onboarding Intro ----------
@app.route("/onboarding")
def onboarding_intro():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("onboarding_intro.html")


@app.route("/onboarding/skip", methods=["POST"])
def onboarding_skip():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/onboarding/start", methods=["POST"])
def onboarding_start():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("onboarding_step", step=1))


# ---------- Onboarding Steps ----------
@app.route("/onboarding/step/<int:step>", methods=["GET", "POST"])
def onboarding_step(step: int):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if step < 1:
        return redirect(url_for("onboarding_step", step=1))
    if step > 10:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        key = f"q{step}"
        answer_value = ""

        # Step 1 / Step 3: radio
        if "answer" in request.form:
            answer_value = request.form.get("answer", "").strip()

        # Step 2: languages (multi)
        elif "languages" in request.form:
            langs = request.form.getlist("languages")
            other_text = request.form.get("other_text", "").strip()
            payload = {"languages": langs}
            if "other" in langs and other_text:
                payload["other_text"] = other_text
            answer_value = json.dumps(payload, ensure_ascii=False)

        # Step 4: genres 3-5
        elif "genres" in request.form:
            genres = request.form.getlist("genres")
            other_text = request.form.get("other_text", "").strip()

            if len(genres) < 3 or len(genres) > 5:
                flash("Please choose from 3 to 5 genres.")
                return redirect(url_for("onboarding_step", step=4))

            payload = {"genres": genres}
            if "other" in genres and other_text:
                payload["other_text"] = other_text
            answer_value = json.dumps(payload, ensure_ascii=False)

        # Step 5: avoid genres
        elif "avoid_genres" in request.form:
            avoid = request.form.getlist("avoid_genres")
            other_text = request.form.get("other_text", "").strip()
            payload = {"avoid_genres": avoid}
            if "other" in avoid and other_text:
                payload["other_text"] = other_text
            answer_value = json.dumps(payload, ensure_ascii=False)

        # save answer (upsert)
        if answer_value:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO onboarding_answers (user_id, question_key, answer)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_key) DO UPDATE SET answer=excluded.answer
            """, (session["user_id"], key, answer_value))
            conn.commit()
            conn.close()

        if step >= 10:
            return redirect(url_for("dashboard"))
        return redirect(url_for("onboarding_step", step=step + 1))

    # GET: render
    if step == 1:
        return render_template("onboarding_step_1.html")
    if step == 2:
        return render_template("onboarding_step_2.html")
    if step == 3:
        return render_template("onboarding_step_3.html")
    if step == 4:
        return render_template("onboarding_step_4.html")
    if step == 5:
        return render_template("onboarding_step_5.html")
    if step == 6:
        return render_template("onboarding_step_6.html")
    if step == 7:
        return render_template("onboarding_step_7.html")
    if step == 8:
        return render_template("onboarding_step_8.html")
    if step == 9:
        return render_template("onboarding_step_9.html")
    

    return render_template("onboarding_step_placeholder.html", step=step)


if __name__ == "__main__":
    app.run(debug=True)
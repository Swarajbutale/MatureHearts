from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, os, hashlib, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "silverheart_secret_2024"
DB = "silverheart.db"

# ── DB Setup ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            status TEXT,
            location TEXT,
            bio TEXT,
            interests TEXT,
            looking_for TEXT,
            avatar_color TEXT DEFAULT '#C8956C',
            avatar_letter TEXT DEFAULT 'S',
            joined TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            liker_id INTEGER,
            liked_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(liker_id, liked_id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            body TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            read INTEGER DEFAULT 0
        );
        """)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def seed_demo_users():
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return
        demos = [
            ("Margaret W.", "margaret@demo.com", hash_pw("demo"), 62, "Female", "Widowed",
             "Delhi", "Retired teacher who loves gardening and classical music. Looking for someone to share morning walks and evening chai.",
             "Gardening,Music,Reading,Yoga", "Male", "#7B9E87", "M"),
            ("Rajesh K.", "rajesh@demo.com", hash_pw("demo"), 58, "Male", "Divorced",
             "Mumbai", "Retired engineer. Love cooking, cricket, and long drives. My kids are grown up and I'm ready to find companionship again.",
             "Cooking,Cricket,Travel,Movies", "Female", "#6B8CAE", "R"),
            ("Sunita P.", "sunita@demo.com", hash_pw("demo"), 51, "Female", "Divorced",
             "Pune", "Art teacher and weekend painter. I believe life begins again at 50. Looking for someone genuine and kind.",
             "Painting,Travel,Food,Dancing", "Male", "#C4768E", "S"),
            ("Vikram S.", "vikram@demo.com", hash_pw("demo"), 67, "Male", "Widowed",
             "Bangalore", "Retired doctor. I enjoy reading, philosophy, and quiet evenings. My grandchildren keep me young at heart.",
             "Reading,Philosophy,Cooking,Chess", "Female", "#8B7355", "V"),
            ("Anita M.", "anita@demo.com", hash_pw("demo"), 54, "Female", "Single",
             "Chennai", "Business owner and travel enthusiast. Never married by choice, now open to finding a true partner for life's next chapter.",
             "Travel,Yoga,Food,Music", "Male", "#9B7EBD", "A"),
            ("Suresh N.", "suresh@demo.com", hash_pw("demo"), 60, "Male", "Widowed",
             "Hyderabad", "Software consultant. Love trekking, photography, and learning new things. My heart is ready to love again.",
             "Trekking,Photography,Technology,Movies", "Female", "#5B8FA8", "S"),
        ]
        for d in demos:
            db.execute("""INSERT OR IGNORE INTO users
                (name,email,password,age,gender,status,location,bio,interests,looking_for,avatar_color,avatar_letter)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", d)

# ── Helpers ───────────────────────────────────────────────────────────────────

def current_user():
    if "user_id" in session:
        with get_db() as db:
            return db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return None

def get_matches(user_id):
    """People who mutually liked each other."""
    with get_db() as db:
        return db.execute("""
            SELECT u.* FROM users u
            JOIN likes l1 ON l1.liked_id = u.id AND l1.liker_id = ?
            JOIN likes l2 ON l2.liked_id = ? AND l2.liker_id = u.id
        """, (user_id, user_id)).fetchall()

def unread_count(user_id):
    with get_db() as db:
        return db.execute("SELECT COUNT(*) FROM messages WHERE receiver_id=? AND read=0", (user_id,)).fetchone()[0]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if current_user():
        return redirect(url_for("discover"))
    return render_template("landing.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        f = request.form
        name = f["name"].strip()
        email = f["email"].strip().lower()
        pw = f["password"]
        age = int(f["age"])
        gender = f["gender"]
        status = f["status"]
        location = f["location"].strip()
        bio = f.get("bio","").strip()
        interests = f.get("interests","")
        looking_for = f.get("looking_for","")

        if age < 45:
            flash("SilverHeart is for people aged 45 and above.", "error")
            return redirect(url_for("register"))

        colors = ["#C8956C","#7B9E87","#6B8CAE","#C4768E","#9B7EBD","#8B7355","#5B8FA8"]
        import random
        color = random.choice(colors)
        letter = name[0].upper() if name else "S"

        try:
            with get_db() as db:
                db.execute("""INSERT INTO users
                    (name,email,password,age,gender,status,location,bio,interests,looking_for,avatar_color,avatar_letter)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (name, email, hash_pw(pw), age, gender, status, location, bio, interests, looking_for, color, letter))
                user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                session["user_id"] = user["id"]
            return redirect(url_for("discover"))
        except sqlite3.IntegrityError:
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=? AND password=?",
                              (email, hash_pw(pw))).fetchone()
        if user:
            session["user_id"] = user["id"]
            return redirect(url_for("discover"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/discover")
def discover():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    with get_db() as db:
        # Exclude self and already-liked
        liked_ids = [r["liked_id"] for r in db.execute("SELECT liked_id FROM likes WHERE liker_id=?", (u["id"],)).fetchall()]
        exclude = liked_ids + [u["id"]]
        placeholders = ",".join("?" * len(exclude))
        profiles = db.execute(f"""
            SELECT * FROM users WHERE id NOT IN ({placeholders})
            ORDER BY RANDOM() LIMIT 10
        """, exclude).fetchall()
    unread = unread_count(u["id"])
    matches = get_matches(u["id"])
    return render_template("discover.html", user=u, profiles=profiles, unread=unread, match_count=len(matches))

@app.route("/like/<int:target_id>", methods=["POST"])
def like(target_id):
    u = current_user()
    if not u:
        return jsonify({"error": "not logged in"}), 401
    with get_db() as db:
        try:
            db.execute("INSERT INTO likes (liker_id, liked_id) VALUES (?,?)", (u["id"], target_id))
        except sqlite3.IntegrityError:
            pass
        # Check mutual
        mutual = db.execute("SELECT id FROM likes WHERE liker_id=? AND liked_id=?", (target_id, u["id"])).fetchone()
        matched = mutual is not None
    return jsonify({"matched": matched})

@app.route("/pass/<int:target_id>", methods=["POST"])
def pass_profile(target_id):
    # Just acknowledge (no DB action needed for pass in basic version)
    return jsonify({"ok": True})

@app.route("/matches")
def matches():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    match_list = get_matches(u["id"])
    unread = unread_count(u["id"])
    return render_template("matches.html", user=u, matches=match_list, unread=unread, match_count=len(match_list))

@app.route("/chat/<int:other_id>")
def chat(other_id):
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    with get_db() as db:
        other = db.execute("SELECT * FROM users WHERE id=?", (other_id,)).fetchone()
        msgs = db.execute("""
            SELECT * FROM messages
            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
            ORDER BY sent_at ASC
        """, (u["id"], other_id, other_id, u["id"])).fetchall()
        db.execute("UPDATE messages SET read=1 WHERE receiver_id=? AND sender_id=?", (u["id"], other_id))
    unread = unread_count(u["id"])
    match_count = len(get_matches(u["id"]))
    return render_template("chat.html", user=u, other=other, messages=msgs, unread=unread, match_count=match_count)

@app.route("/send_message", methods=["POST"])
def send_message():
    u = current_user()
    if not u:
        return jsonify({"error": "not logged in"}), 401
    data = request.json
    with get_db() as db:
        db.execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (?,?,?)",
                   (u["id"], data["receiver_id"], data["body"]))
    return jsonify({"ok": True, "time": datetime.now().strftime("%I:%M %p")})

@app.route("/profile/<int:uid>")
def profile(uid):
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    with get_db() as db:
        person = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    unread = unread_count(u["id"])
    match_count = len(get_matches(u["id"]))
    return render_template("profile.html", user=u, person=person, unread=unread, match_count=match_count)

@app.route("/my_profile", methods=["GET","POST"])
def my_profile():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        with get_db() as db:
            db.execute("""UPDATE users SET bio=?, location=?, interests=?, looking_for=?
                          WHERE id=?""",
                       (f.get("bio",""), f.get("location",""), f.get("interests",""), f.get("looking_for",""), u["id"]))
        flash("Profile updated!", "success")
        return redirect(url_for("my_profile"))
    unread = unread_count(u["id"])
    match_count = len(get_matches(u["id"]))
    return render_template("my_profile.html", user=u, unread=unread, match_count=match_count)

if __name__ == "__main__":
    init_db()
    seed_demo_users()
    app.run(debug=True)

init_db()
seed_demo_users()
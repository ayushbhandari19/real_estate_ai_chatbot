from flask import Flask, request, jsonify, render_template, Response
from functools import wraps
import os
import re
import sqlite3
from dotenv import load_dotenv

# ---------------- App setup ----------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
app = Flask(__name__)

# ---------------- Admin auth ----------------
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

def admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != ADMIN_PASSWORD:
            return Response(
                "Admin access required",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

# ---------------- Utilities ----------------
def extract_budget(text):
    match = re.search(r'(\d+)\s*(lakh|crore)', text.lower())
    return match.group(0) if match else None

# ---------------- Database ----------------
def get_db():
    conn = sqlite3.connect("leads.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT
        )
    """)
    return conn

# ---------------- Memory ----------------
sessions = {}

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "")
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"error": "Message required"}), 400

    sessions.setdefault(session_id, []).append(message)

    budget = extract_budget(message)

    if budget:
        reply = f"Great 👍 Budget noted: {budget}. Which city are you interested in?"
    elif "buy" in message.lower():
        reply = "Are you looking to buy a flat, house, or plot?"
    elif "rent" in message.lower():
        reply = "Sure! Which city and budget are you looking to rent in?"
    else:
        reply = "I can help with buying, selling, or renting properties."

    return jsonify({"reply": reply})

@app.route("/lead", methods=["POST"])
def capture_lead():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO leads (name, phone, email) VALUES (?, ?, ?)",
        (data.get("name"), data.get("phone"), data.get("email"))
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "lead captured"})

@app.route("/admin")
@admin_auth
def admin_dashboard():
    return render_template("admin.html")

@app.route("/admin/data")
@admin_auth
def admin_data():
    conn = get_db()
    rows = conn.execute("SELECT name, phone, email FROM leads").fetchall()
    conn.close()

    return jsonify({
        "leads": [{"name": r[0], "phone": r[1], "email": r[2]} for r in rows],
        "sessions": sessions
    })

# ---------------- Run ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)

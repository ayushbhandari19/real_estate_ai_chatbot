from flask import Flask, request, jsonify, render_template, Response
from functools import wraps
import os
import re
import sqlite3
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage


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
def detect_intent(text):
    text = text.lower()
    if any(w in text for w in ["buy", "purchase", "investment"]):
        return "BUY"
    if any(w in text for w in ["rent", "lease"]):
        return "RENT"
    return None

def extract_city(text):
    # simple placeholder (can improve later)
    cities = ["pune", "mumbai", "delhi", "bangalore", "hyderabad"]
    for city in cities:
        if city in text.lower():
            return city.title()
    return None

def extract_property_type(text):
    if "1bhk" in text.lower():
        return "1 BHK"
    if "2bhk" in text.lower():
        return "2 BHK"
    if "3bhk" in text.lower():
        return "3 BHK"
    if "villa" in text.lower():
        return "Villa"
    return None

def is_conversation_complete(session):
    return all([
        session.get("intent"),
        session.get("property_type"),
        session.get("budget"),
        session.get("city")
    ])


@app.route("/chat", methods=["POST"])
def chat():

    MAX_SESSIONS = 1000
    if len(sessions) > MAX_SESSIONS:
        sessions.clear()

    data = request.get_json() or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"error": "Message required"}), 400

    # Initialize session
    sessions.setdefault(session_id, {
        "messages": [],
        "intent": None,
        "budget": None,
        "city": None,
        "property_type": None
    })

    session = sessions[session_id]
    session["messages"].append(message)

    # Extract info
    intent = detect_intent(message)
    budget = extract_budget(message)
    city = extract_city(message)
    prop_type = extract_property_type(message)

    if intent:
        session["intent"] = intent
    if budget:
        session["budget"] = budget
    if city:
        session["city"] = city
    if prop_type:
        session["property_type"] = prop_type

    # Ask for missing info
    if not session["intent"]:
        reply = "Are you looking to buy or rent a property?"
        return jsonify({"reply": reply})

    if not session["property_type"]:
        reply = "What type of property are you looking for? (1BHK, 2BHK, Villa, etc.)"
        return jsonify({"reply": reply})

    if not session["budget"]:
        reply = "What is your budget range?"
        return jsonify({"reply": reply})

    if not session["city"]:
        reply = "Which city or area are you interested in?"
        return jsonify({"reply": reply})

    # ✅ Conversation complete → trigger CTA
    reply = (
        f"Perfect! ✅ Here’s what I’ve understood:\n\n"
        f"• Purpose: {session['intent'].title()}\n"
        f"• Property: {session['property_type']}\n"
        f"• City: {session['city']}\n"
        f"• Budget: {session['budget']}\n\n"
        f"Would you like our property expert to contact you with matching options?"
    )

    return jsonify({
        "reply": reply,
        "show_lead_form": True
    })



@app.route("/lead", methods=["POST"])
def capture_lead():
    data = request.get_json()

    # Save to DB
    conn = get_db()
    conn.execute(
        "INSERT INTO leads (name, phone, email) VALUES (?, ?, ?)",
        (data.get("name"), data.get("phone"), data.get("email"))
    )
    conn.commit()
    conn.close()

    # Send email (non-blocking safety)
    try:
        send_email_notification(data)
    except Exception as e:
        print("Email notification failed:", e)

    return jsonify({"status": "lead captured"})



def send_email_notification(lead):
    msg = EmailMessage()
    msg["Subject"] = "New Real Estate Lead"
    msg["From"] = os.environ.get("EMAIL_USER")
    msg["To"] = os.environ.get("EMAIL_USER")

    msg.set_content(f"""
New lead received:

Name: {lead.get('name')}
Phone: {lead.get('phone')}
Email: {lead.get('email')}
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.environ.get("EMAIL_USER"),
            os.environ.get("EMAIL_PASS")
        )
        smtp.send_message(msg)



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

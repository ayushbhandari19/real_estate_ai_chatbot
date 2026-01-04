from flask import Flask, request, jsonify, render_template
import os
import re
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)

# ---------------- Utilities ----------------
def extract_budget(text):
    match = re.search(r'(\d+)\s*(lakh|crore)', text.lower())
    return match.group(0) if match else None

# ---------------- In-memory stores ----------------
sessions = {}
leads = []

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

    return jsonify({
        "reply": reply,
        "session_id": session_id
    })

@app.route("/lead", methods=["POST"])
def capture_lead():
    data = request.get_json()
    leads.append({
        "name": data.get("name"),
        "phone": data.get("phone"),
        "email": data.get("email")
    })
    return jsonify({"status": "lead captured"})

@app.route("/leads", methods=["GET"])
def view_leads():
    return jsonify(leads)

@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html")


@app.route("/admin/data")
def admin_data():
    return jsonify({
        "leads": leads,
        "sessions": sessions
    })

# ---------------- Run ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)


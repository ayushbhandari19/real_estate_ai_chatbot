from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from system_prompt import SYSTEM_PROMPT

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

print("OPENAI KEY FROM APP:", os.getenv("OPENAI_API_KEY"))


app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "message": "Chatbot API is live 🚀",
        "endpoint": "/chat (POST)"
    })

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        print("CHAT ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(debug=True, port=port)

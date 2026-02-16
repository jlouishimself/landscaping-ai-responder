import os
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_verify_token")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are an AI assistant for a landscaping company.

Your goals:
1. Respond professionally and briefly.
2. Ask what service they need.
3. Ask for their address or zip code.
4. Ask for their phone number.
5. Keep responses short and clear.
"""

@app.route("/")
def home():
    return "AI Landscaping Responder is Running"

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "No data", 400

    # For now just test OpenAI call
    test_message = "Customer wants lawn mowing quote"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": test_message}
        ]
    )

    reply = response.choices[0].message.content
    print("AI RESPONSE:", reply)

    return "OK", 200

if __name__ == "__main__":
    # Use Render's dynamic port if provided
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

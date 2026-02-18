import os
import re
import json
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Env vars (set these in Render)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "landscape123").strip()

# Hard fail if key missing (better than hanging)
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Set it in Render Environment Variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are AutoReply Pro, a messaging assistant for small businesses (restaurants, auto detailing,
landscaping, contractors, salons, etc.).

Primary goal: convert messages into bookings/leads.

Rules:
- Be professional, friendly, and concise.
- Ask at most 1–2 questions per reply.
- Move toward one of these outcomes:
  (A) book an appointment
  (B) collect phone number
  (C) collect location (city/zip) + service requested
- If the user asks for pricing, ask one clarifying question (service + location) then offer a range.
- Do NOT mention you are an AI unless explicitly asked.
- If asked if you're automated, say you're an automated assistant that helps the business respond fast.
"""

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def extract_phone(text: str):
    # Basic US phone extraction (good enough for MVP)
    m = re.search(r'(\+?1[\s\-\.]?)?(\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})', text)
    return m.group(0) if m else None

def generate_reply(user_text: str):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()

@app.get("/")
def home():
    return "AutoReply Pro Brain is Running"

# Simple JSON test endpoint (useful before Facebook wiring)
@app.post("/api/reply")
def api_reply():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    phone = extract_phone(text)
    reply = generate_reply(text)

    # Minimal logging (Render logs will show it)
    app.logger.info(json.dumps({
        "ts": now_iso(),
        "route": "/api/reply",
        "text": text,
        "phone_detected": phone,
        "reply": reply[:240]
    }))

    return jsonify({"reply": reply, "phone_detected": phone})

# Meta verification endpoint (for later)
@app.get("/webhook")
def webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge or "", 200

    return "Verification failed", 403

# Incoming Meta messages endpoint (we'll complete the "send reply back" in next step)
@app.post("/webhook")
def webhook_incoming():
    data = request.get_json(silent=True) or {}

    # For now: just log incoming payload so we know Meta is reaching us
    app.logger.info(json.dumps({
        "ts": now_iso(),
        "route": "/webhook",
        "payload_keys": list(data.keys())
    }))

    # We respond 200 quickly so Meta doesn't retry.
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

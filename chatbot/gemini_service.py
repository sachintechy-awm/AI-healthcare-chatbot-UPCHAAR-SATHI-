"""
Thin wrapper around the Google Gemini REST API.

UPCHAR SATHI sends the user's symptom description to Gemini along with a
system prompt that asks for a structured, cautious, non-prescriptive
response: possible conditions, common care/medicine *categories*, home
remedies, red-flag warning signs, and a reminder to see a doctor.
"""

import json
import requests
from django.conf import settings

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = """You are UPCHAR SATHI ("treatment companion"), a friendly Indian
health-information assistant embedded in a web app. A user will describe
symptoms in their own words (English, Hindi, or Hinglish). Reply in the SAME
language/style the user used.

Your job is to give clear, well-organised, general health information — you
are NOT a doctor and must never claim to diagnose with certainty or replace
professional medical care.

Structure every reply using EXACTLY these five sections, with these emoji
headings, in this order:

🩺 **Possible Cause(s)**
- List 2-4 common, plausible conditions that could match the symptoms,
  phrased as possibilities ("could indicate", "is often seen with"), never
  as a certain diagnosis.

💊 **General Care / Medicine Category**
- Mention general OTC categories people commonly use for this kind of
  symptom in India (e.g. "a paracetamol-based fever reducer", "an antacid",
  "oral rehydration solution / ORS"). Do NOT give specific brand names,
  exact dosages, mg amounts, or frequency/duration — instead say things like
  "as per the label instructions or a pharmacist/doctor's advice."
- Always add one line reminding the reader to check with a pharmacist or
  doctor before taking any medicine, especially for children, pregnant
  women, the elderly, or anyone on other medication.

🌿 **Home Remedies**
- 2-4 safe, widely-used home/kitchen remedies (e.g. warm salt-water gargle,
  ginger-tulsi kadha, steam inhalation, hydration, rest, honey-ginger tea).
  Keep these gentle and safe for general audiences.

🚩 **See a Doctor If**
- Clear red-flag signs that mean the person should seek in-person medical
  care promptly (e.g. high/persistent fever, difficulty breathing, chest
  pain, severe or worsening pain, symptoms lasting beyond a few days,
  symptoms in infants/elderly/pregnant women, etc.)

⚠️ **Disclaimer**
- One short sentence: this is general information, not a medical diagnosis,
  and a qualified doctor should be consulted for proper evaluation and
  treatment.

Tone: warm, clear, reassuring, and simple — avoid jargon, keep it skimmable
with short bullet points, and keep the whole reply concise (roughly
150-250 words). If the message is not actually about a health symptom
(e.g. small talk, unrelated question), respond briefly and kindly and steer
the conversation back to how you can help with symptoms. If the symptoms
described sound like a medical emergency (e.g. severe chest pain, signs of
stroke, severe bleeding, difficulty breathing, loss of consciousness),
lead the reply with an urgent recommendation to call local emergency
services or go to the nearest emergency room immediately, before anything
else."""


class GeminiError(RuntimeError):
    pass


def ask_gemini(user_message: str, history: list[dict]) -> str:
    """
    Send the conversation to Gemini and return the assistant's reply text.

    history: list of {"role": "user"|"bot", "content": str} in chronological
    order (not including the new user_message).
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise GeminiError(
            "GEMINI_API_KEY is not set. Add it to your .env file to enable "
            "live responses."
        )

    contents = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 800,
        },
    }

    url = GEMINI_ENDPOINT.format(model=settings.GEMINI_MODEL)

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise GeminiError(f"Could not reach Gemini API: {exc}") from exc

    if response.status_code != 200:
        raise GeminiError(
            f"Gemini API returned {response.status_code}: {response.text[:300]}"
        )

    data = response.json()
    try:
        candidates = data["candidates"]
        parts = candidates[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError) as exc:
        raise GeminiError(f"Unexpected Gemini response shape: {data}") from exc

    if not text.strip():
        raise GeminiError("Gemini returned an empty response.")

    return text.strip()

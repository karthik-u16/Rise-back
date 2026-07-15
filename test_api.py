from dotenv import load_dotenv
load_dotenv()

import os
import requests

api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

payload = {
    "contents": [
        {"parts": [{"text": "In one short sentence, motivate someone to finish their workout."}]}
    ]
}

response = requests.post(url, json=payload, timeout=15)
response.raise_for_status()
data = response.json()

print(data["candidates"][0]["content"]["parts"][0]["text"])
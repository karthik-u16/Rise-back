from dotenv import load_dotenv
load_dotenv()

import os
import requests

api_key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

payload = {
    "contents": [
        {"parts": [{"text": "In one short sentence, motivate someone to finish their workout."}]}
    ]
}

response = requests.post(url, json=payload, timeout=30)
print("Status code:", response.status_code)
print(response.text)
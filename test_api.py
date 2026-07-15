from dotenv import load_dotenv
load_dotenv()

import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="In one short sentence, motivate someone to finish their workout."
)

print(response.text)
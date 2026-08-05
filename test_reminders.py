import requests
import os
from dotenv import load_dotenv
load_dotenv()

response = requests.post(
    "http://127.0.0.1:5000/api/send-reminders",
    headers={"X-Cron-Secret": os.environ["CRON_SECRET"]}
)
print("Status code:", response.status_code)
print(response.json())
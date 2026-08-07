import requests

base = "https://rise-back-rfuo.onrender.com"

login_res = requests.post(f"{base}/api/login", json={
    "username": "karthikeyan",
    "password": "77"
})
token = login_res.json()["token"]
print("Login OK.")

headers = {"Authorization": f"Bearer {token}"}

# First message, no history yet
res1 = requests.post(f"{base}/api/mentor-chat", headers=headers, json={
    "message": "How's my progress going?",
    "history": []
})
print("First message status:", res1.status_code)
data1 = res1.json()
print(data1)

# Second message, sending back the history we got
res2 = requests.post(f"{base}/api/mentor-chat", headers=headers, json={
    "message": "What should I eat today?",
    "history": data1["history"]
})
print("\nSecond message status:", res2.status_code)
print(res2.json())
import requests

base = "https://rise-back-rfuo.onrender.com"

login_res = requests.post(f"{base}/api/login", json={
    "username": "karthikeyan",
    "password": "77"
})
token = login_res.json()["token"]
print("Login OK.")

headers = {"Authorization": f"Bearer {token}"}

# Test GET - fetch level 1 challenges
get_res = requests.get(f"{base}/api/challenges/1", headers=headers)
print("GET status:", get_res.status_code)
print(get_res.json())

# Test POST - complete level 1 challenge
post_res = requests.post(f"{base}/api/complete/1", headers=headers)
print("POST status:", post_res.status_code)
print(post_res.json())
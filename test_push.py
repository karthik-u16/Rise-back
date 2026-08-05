import requests

base = "http://127.0.0.1:5000"

login_res = requests.post(f"{base}/api/login", json={
    "username": "karthikeyan",
    "password": "77"
})
token = login_res.json()["token"]
print("Login OK.")

headers = {"Authorization": f"Bearer {token}"}
push_res = requests.post(f"{base}/api/test-push", headers=headers)
print("Status code:", push_res.status_code)
print(push_res.json())
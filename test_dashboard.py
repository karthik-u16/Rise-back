import requests

base = "http://127.0.0.1:5000"

login_res = requests.post(f"{base}/api/login", json={
    "username": "karthikeyan",
    "password": "77"
})
token = login_res.json()["token"]
print("Login OK, token received.")

headers = {"Authorization": f"Bearer {token}"}
dash_res = requests.get(f"{base}/api/dashboard", headers=headers)
print("Status code:", dash_res.status_code)
print(dash_res.json())
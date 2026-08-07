import requests

base = "https://rise-back-rfuo.onrender.com"

login_res = requests.post(f"{base}/api/login", json={
    "username": "karthikeyan",
    "password": "77"
})
token = login_res.json()["token"]
print("Login OK.")

headers = {"Authorization": f"Bearer {token}"}

# Test GET
get_res = requests.get(f"{base}/api/workouts", headers=headers)
print("GET status:", get_res.status_code)
print(get_res.json())

# Test POST - log a workout
post_res = requests.post(f"{base}/api/workouts", headers=headers, json={
    "exercise_name": "Push Ups",
    "sets": 3,
    "reps": 12,
    "duration_minutes": 5
})
print("POST status:", post_res.status_code)
print(post_res.json())
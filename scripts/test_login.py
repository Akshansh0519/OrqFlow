import json
import urllib.request

url = "http://127.0.0.1:8000/api/auth/login"
data = json.dumps({"email": "test@orqflow.ai", "password": "password123"}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req) as resp:
        print("LOGIN SUCCESS:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("LOGIN FAILED:", e.code, e.read().decode())
except Exception as e:
    print("CONNECTION ERROR:", str(e))

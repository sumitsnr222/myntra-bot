import urllib.request, json

# Test OTP send for user's number
data = json.dumps({"phone": "9992443292"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/accounts/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
print("Sending OTP to 9992443292...")
resp = urllib.request.urlopen(req, timeout=60)
result = json.loads(resp.read().decode())
print(json.dumps(result, indent=2))

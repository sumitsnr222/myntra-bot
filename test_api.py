import urllib.request, json
data = json.dumps({"phone":"9876543210","cookie_string":"at=test123; ut=user456; mynt-ulc=testcookie"}).encode()
req = urllib.request.Request("http://localhost:8000/api/accounts/setcookie", data=data, headers={"Content-Type":"application/json"}, method="POST")
resp = urllib.request.urlopen(req)
print(resp.read().decode())

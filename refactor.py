import re
import os
import json

print("Starting refactor...")

DATA = "backend/data"
os.makedirs(DATA, exist_ok=True)

# 1. Update myntra_client.py to_dict()
content = open('backend/myntra_client.py', encoding='utf-8').read()
if '"owner": self.owner,' not in content and '"owner": getattr(self, "owner", ""),' not in content:
    if '"proxy": getattr(self, "proxy", None),' in content:
        content = content.replace('"proxy": getattr(self, "proxy", None),', '"proxy": getattr(self, "proxy", None),\n            "owner": getattr(self, "owner", ""),')
    elif '"proxy": self.proxy,' in content:
        content = content.replace('"proxy": self.proxy,', '"proxy": self.proxy,\n            "owner": self.owner,')
    else:
        content = content.replace('"logged_in": self.logged_in,', '"proxy": getattr(self, "proxy", None),\n            "owner": getattr(self, "owner", ""),\n            "logged_in": self.logged_in,')
    open('backend/myntra_client.py', 'w', encoding='utf-8').write(content)

# 2. Update api.py
api_content = open('backend/api.py', encoding='utf-8').read()

auth_models = '''class AuthRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    phone: str
    owner: str = ""
'''
api_content = re.sub(r'class LoginRequest\(BaseModel\):\n\s+phone: str', auth_models, api_content)

auth_globals = '''USERS_FILE = os.path.join(DATA, "users.json")

def load_users():
    if os.path.exists(USERS_FILE):
        return json.load(open(USERS_FILE, encoding='utf-8'))
    admin = {"s09698840@gmail.com": {"password": "870881@Qwer", "role": "admin"}}
    save_users(admin)
    return admin

def save_users(users):
    json.dump(users, open(USERS_FILE, "w", encoding='utf-8'))

users_db = load_users()

@app.post("/api/auth/signup")
async def auth_signup(req: AuthRequest):
    if req.email in users_db:
        return {"success": False, "message": "User already exists"}
    users_db[req.email] = {"password": req.password, "role": "user"}
    save_users(users_db)
    return {"success": True, "message": "Signup successful", "role": "user", "token": req.email}

@app.post("/api/auth/login")
async def auth_login(req: AuthRequest):
    user = users_db.get(req.email)
    if not user or user["password"] != req.password:
        return {"success": False, "message": "Invalid credentials"}
    return {"success": True, "role": user["role"], "token": req.email}
'''

if '# ── Auth Routes ──' not in api_content:
    api_content = api_content.replace('# ── API Routes ──', '# ── Auth Routes ──\n' + auth_globals + '\n\n# ── API Routes ──')

dup_check = '''    if phone in accounts:
        return {"success": False, "message": f"Account {phone} already exists in the system!"}

    device = generate_device()'''
if 'Account {phone} already exists in the system!' not in api_content:
    api_content = api_content.replace('    device = generate_device()', dup_check, 1)

api_content = api_content.replace('"device": device, "ctx": ctx, "page": page, "cookies": cookies}', '"device": device, "ctx": ctx, "page": page, "cookies": cookies, "owner": req.owner}')

api_content = api_content.replace('proxy = info.get("proxy")', 'proxy = info.get("proxy")\n        owner = info.get("owner", "")')
api_content = api_content.replace('proxy=proxy)', 'proxy=proxy, owner=owner)')

if 'async def get_stats(owner: str = None):' not in api_content:
    api_content = api_content.replace('async def get_stats():', 'async def get_stats(owner: str = None):')
if 'users_db.get(owner, {}).get("role") !=' not in api_content:
    api_content = api_content.replace('for phone, client in accounts.items():', '''for phone, client in accounts.items():
        if owner and users_db.get(owner, {}).get("role") != "admin" and getattr(client, 'owner', '') != owner:
            continue''')

api_content = api_content.replace('async def list_accounts():\n    return await get_stats()', 'async def list_accounts(owner: str = None):\n    return await get_stats(owner)')

if 'owner=pending_logins.get(phone, {}).get("owner", "")' not in api_content:
    api_content = api_content.replace('client = MyntraClient(phone, device, cookies, proxy=proxy)', 'client = MyntraClient(phone, device, cookies, proxy=proxy, owner=pending_logins.get(phone, {}).get("owner", ""))')

cookie_route = '''
@app.get("/api/accounts/{phone}/cookies")
async def download_cookies(phone: str, owner: str = None):
    client = accounts.get(phone)
    if not client:
        raise HTTPException(404, "Account not found")
    if owner and users_db.get(owner, {}).get("role") != "admin" and getattr(client, 'owner', '') != owner:
        raise HTTPException(403, "Not authorized")
    content = json.dumps(client.cookies, indent=2)
    with open(f"{phone}_cookies.json", "w") as f:
        f.write(content)
    return FileResponse(f"{phone}_cookies.json", filename=f"{phone}_cookies.txt")
'''
if '/api/accounts/{phone}/cookies' not in api_content:
    api_content = api_content + cookie_route

open('backend/api.py', 'w', encoding='utf-8').write(api_content)
print("Done!")

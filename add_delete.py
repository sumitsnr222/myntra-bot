import re
api_content = open('backend/api.py', encoding='utf-8').read()

delete_route = '''
@app.delete("/api/accounts/{phone}")
async def delete_account(phone: str, owner: str = None):
    if owner and users_db.get(owner, {}).get("role") != "admin":
        raise HTTPException(403, "Only admins can delete accounts")
    if phone in accounts:
        del accounts[phone]
        await save_accounts()
        return {"success": True, "message": "Account deleted"}
    return {"success": False, "message": "Account not found"}
'''

if '/api/accounts/{phone}' not in api_content:
    api_content = api_content + delete_route
    open('backend/api.py', 'w', encoding='utf-8').write(api_content)
    print("Delete route added.")

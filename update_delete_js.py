import os
js = open('frontend/app.js', encoding='utf-8').read()

new_logic = """
    try {
        const r = await fetch(`/api/accounts/${phone}?owner=${currentUser}`, { method: 'DELETE' });
        const data = await r.json();
        if(data.success) {
            alert('Account deleted!');
            refreshAccounts();
        } else {
            alert(data.message);
        }
    } catch(e) {
        console.error(e);
    }
"""

js = js.replace('alert("Delete disabled in demo");', new_logic)
open('frontend/app.js', 'w', encoding='utf-8').write(js)

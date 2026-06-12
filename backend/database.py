"""
Myntra Web Suite — Async JSON-file database helpers
"""
import json
import time
import logging
import aiofiles
import os
DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SESSIONS_FILE = os.path.join(DATA, "accounts.json")
STATS_FILE = os.path.join(DATA, "stats.json")
LOG_FILE = os.path.join(DATA, "bot.log")
logger = logging.getLogger(__name__)


async def load_db(path: str = SESSIONS_FILE) -> dict:
    """Load a JSON database file, return {} on any error."""
    try:
        async with aiofiles.open(path, "r") as f:
            return json.loads(await f.read())
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"DB read error [{path}]: {e}")
        return {}


async def save_db(data: dict, path: str = SESSIONS_FILE):
    """Save data to a JSON database file."""
    try:
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))
    except Exception as e:
        logger.error(f"DB write error [{path}]: {e}")


async def log_action(phone: str, action: str, result: bool):
    """Append one line to the action log."""
    line = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"{phone} | {action} | {'SUCCESS' if result else 'FAIL'}\n"
    )
    try:
        async with aiofiles.open(LOG_FILE, "a") as f:
            await f.write(line)
    except Exception:
        pass


async def bump_stat(key: str, amount: int = 1):
    """Increment a counter in stats.json."""
    s = await load_db(STATS_FILE)
    s[key] = s.get(key, 0) + amount
    await save_db(s, STATS_FILE)


async def get_all_accounts() -> dict:
    """Return all saved accounts."""
    return await load_db(SESSIONS_FILE)


async def get_account(phone: str) -> dict | None:
    """Get a single account by phone number."""
    db = await load_db(SESSIONS_FILE)
    return db.get(phone)


async def save_account(phone: str, data: dict):
    """Save/update an account."""
    db = await load_db(SESSIONS_FILE)
    db[phone] = data
    await save_db(db, SESSIONS_FILE)


async def delete_account(phone: str) -> bool:
    """Delete an account. Returns True if it existed."""
    db = await load_db(SESSIONS_FILE)
    if phone in db:
        del db[phone]
        await save_db(db, SESSIONS_FILE)
        return True
    return False


async def get_stats() -> dict:
    """Return stats + account summary."""
    db = await load_db(SESSIONS_FILE)
    s  = await load_db(STATS_FILE)
    active = sum(1 for v in db.values() if v.get("cookies"))
    return {
        "total_accounts":   len(db),
        "active_sessions":  active,
        "expired_sessions": len(db) - active,
        "tasks_run":        s.get("tasks_run", 0),
        "actions_ok":       s.get("actions_ok", 0),
        "actions_fail":     s.get("actions_fail", 0),
    }


async def get_logs(limit: int = 50) -> list[str]:
    """Return last N log lines."""
    try:
        async with aiofiles.open(LOG_FILE, "r") as f:
            lines = (await f.read()).strip().split("\n")
        return lines[-limit:] if len(lines) > limit else lines
    except FileNotFoundError:
        return []

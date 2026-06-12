import os
import random
import logging

log = logging.getLogger("backend.proxy_manager")

class ProxyManager:
    def __init__(self, proxies_file: str):
        self.proxies = []
        if os.path.exists(proxies_file):
            with open(proxies_file, "r") as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            log.info(f"[ProxyManager] Loaded {len(self.proxies)} proxies from {proxies_file}")
        else:
            log.warning(f"[ProxyManager] Proxies file not found at {proxies_file}")

    def get_random_proxy(self) -> str:
        """Returns a random proxy in the format 'http://IP:PORT' or None if no proxies loaded."""
        if not self.proxies:
            return None
        p = random.choice(self.proxies)
        # Ensure it has a scheme
        if not p.startswith("http"):
            return f"http://{p}"
        return p

# Global proxy manager instance will be initialized in api.py
proxy_manager = None

def init_proxy_manager(filepath: str):
    global proxy_manager
    proxy_manager = ProxyManager(filepath)
    return proxy_manager

def get_proxy_manager() -> ProxyManager:
    return proxy_manager

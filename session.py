from requests import Session

def iter_proxies(path="data/proxy.txt"):
    proxies = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                proxy = line.strip()
                if not proxy or proxy.startswith("#"):
                    continue
                if "://" not in proxy:
                    proxy = "http://" + proxy
                proxies.append(proxy)
    except FileNotFoundError:
        pass
    return proxies

def get_session(proxy_str: str | None = None) -> Session:
    s = Session()
    if proxy_str:
        s.proxies.update({
            "http": proxy_str,
            "https": proxy_str,
        })
    return s
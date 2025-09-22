# Para el cliente de Ddragon, que tiene la data de LoL que se utilizará

import os, json, requests, pathlib

BASE = "https://ddragon.leagueoflegends.com"
CACHE_DIR = pathlib.Path("./cache_dd")

class DDragonClient:
    def __init__(self, lang="en_US"):
        self.lang = lang
        self.version = None
        CACHE_DIR.mkdir(exist_ok=True, parents=True)

    def ensure_latest(self, version="latest"):
        if version == "latest":
            vers = requests.get(f"{BASE}/api/versions.json", timeout=30).json()
            self.version = vers[0]
        else:
            self.version = version
        self._get_json(f"/cdn/{self.version}/data/{self.lang}/champion.json")
        self._get_json(f"/cdn/{self.version}/data/{self.lang}/item.json")
        self._get_json(f"/cdn/{self.version}/data/{self.lang}/runesReforged.json")
        self._get_json(f"/cdn/{self.version}/data/{self.lang}/summoner.json")
        return self.version

    def _cache_path(self, path):
        safe = path.strip("/").replace("/", "_")
        return CACHE_DIR / f"{safe}.json"

    def _get_json(self, path):
        cp = self._cache_path(path)
        if cp.exists():
            return json.loads(cp.read_text(encoding="utf-8"))
        url = f"{BASE}{path}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        cp.write_text(r.text, encoding="utf-8")
        return r.json()

    def champions(self):
        data = self._get_json(f"/cdn/{self.version}/data/{self.lang}/champion.json")
        return data["data"]  

    def items(self):
        return self._get_json(f"/cdn/{self.version}/data/{self.lang}/item.json")["data"]

    def runes(self):
        return self._get_json(f"/cdn/{self.version}/data/{self.lang}/runesReforged.json")

    def summoners(self):
        return self._get_json(f"/cdn/{self.version}/data/{self.lang}/summoner.json")["data"]

    def champ_tags(self, champ_name_lower):
        champs = self.champions()
        for k, v in champs.items():
            if k.lower() == champ_name_lower:
                return v.get("tags", []), v
        return [], None
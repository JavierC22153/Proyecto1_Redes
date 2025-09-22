import os, json, requests, re

# Configuración de Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  

SYSTEM = """You are a strict intent extractor for League of Legends.
Input: free text like "I want to play Darius tank against Garen, Maokai, Ahri, Jinx, Lulu".
Output JSON:
{"ally_champion":"<string>","ally_characteristic":"AD|AP|TANK","enemy_team":["<5 champs>"]}"""

def _fallback(text: str):
    t = text.lower()
    
    # Detectar característica
    char = "TANK" if ("tank" in t) else ("AP" if " ap" in t or "mage" in t else "AD")
    
    # Detectar campeón aliado
    ally_patterns = [
        r"(?:play|use|pick|main)\s+([a-zA-Z'\\.]+)",
        r"(?:as|with)\s+([a-zA-Z'\\.]+)",
        r"^([a-zA-Z'\\.]+)\s+(?:tank|ap|ad|vs|against)"
    ]
    
    ally = None
    for pattern in ally_patterns:
        match = re.search(pattern, t)
        if match:
            ally = match.group(1)
            break
    
    if not ally:
        ally = "darius"  # default
    
    # Detectar enemigos
    enemies = []
    if "against" in t or "vs" in t:
        # Separar la parte de enemigos
        if "against" in t:
            enemy_part = t.split("against", 1)[1]
        else:
            enemy_part = t.split("vs", 1)[1]
        
        # Extraer nombres de campeones (palabras que parecen nombres)
        potential_enemies = re.findall(r'\b[a-zA-Z\']{3,}\b', enemy_part)
        enemies = [e for e in potential_enemies if e not in ['and', 'the', 'with']]
    
    # Asegurar que tengamos 5 enemigos
    default_enemies = ["garen", "maokai", "ahri", "jinx", "lulu"]
    if len(enemies) < 5:
        enemies.extend(default_enemies[len(enemies):])
    
    enemies = enemies[:5]  # Máximo 5
    
    return {
        "ally_champion": ally.lower(),
        "ally_characteristic": char,
        "enemy_team": enemies
    }

def parse_intent_text(text: str):
    # Si no hay API key de Groq, usar fallback
    if not GROQ_API_KEY:
        print("Groq API no configurada, usando parser básico")
        return _fallback(text)
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text}
            ]
        }
        
        r = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        
        content = r.json()["choices"][0]["message"]["content"]
        
        # Intentar parsear JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Buscar JSON en la respuesta
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if not m:
                print("Groq falló, usando parser básico")
                return _fallback(text)
            data = json.loads(m.group(0))
        
        # Normalizar datos
        data["ally_champion"] = data.get("ally_champion", "darius").lower()
        data["ally_characteristic"] = data.get("ally_characteristic", "AD").upper()
        data["enemy_team"] = [e.lower() for e in data.get("enemy_team", [])][:5]
        
        # Asegurar 5 enemigos
        if len(data["enemy_team"]) < 5:
            default_enemies = ["garen", "maokai", "ahri", "jinx", "lulu"]
            data["enemy_team"].extend(default_enemies[len(data["enemy_team"]):])
        
        return data
        
    except Exception as e:
        print(f"⚠️ Error con Groq API ({e}), usando parser básico")
        return _fallback(text)
# Para analizar los equipos enemigos

from typing import List, Dict, Tuple

AD_TAGS = {"Fighter", "Marksman", "Assassin"}
AP_TAGS = {"Mage", "Support"}
TANK_TAGS = {"Tank"}

CC_KEYWORDS = {
    "stun", "root", "knockup", "knock up", "airborne", "sleep",
    "charm", "taunt", "fear", "suppression", "silence", "slow"
}
HEAL_SHIELD_KEYS = {"heal", "healing", "shield", "shielding", "barrier"}

def _severity_from_hits(hits: int) -> str:
    if hits >= 5: return "very_high"
    if hits >= 3: return "high"
    if hits >= 2: return "medium"
    if hits >= 1: return "low"
    return "none"

def analyze_enemy_comp(dd, enemy_team: List[str]) -> Dict:
    ad_score = 0
    ap_score = 0
    tank_count = 0
    cc_hits = 0
    heal_shield_hits = 0

    for name in enemy_team:
        if not name:
            continue
        tags, meta = dd.champ_tags(name.lower())
        if not meta:
            continue

        tagset = set(tags or [])
        if tagset & AD_TAGS:
            ad_score += 1
        if tagset & AP_TAGS:
            ap_score += 1
        if tagset & TANK_TAGS:
            tank_count += 1

        parts = []
        if meta.get("passive"):
            parts.append(meta["passive"])
        if meta.get("spells"):
            parts.extend(meta["spells"])

        for p in parts:
            desc = (p.get("description") or p.get("sanitizedDescription") or "").lower()
            if any(k in desc for k in CC_KEYWORDS):
                cc_hits += 1
            if any(k in desc for k in HEAL_SHIELD_KEYS):
                heal_shield_hits += 1

    total = max(1, len([x for x in enemy_team if x]))
    ad_pct = round(100 * ad_score / total)
    ap_pct = round(100 * ap_score / total)

    if ad_score >= 2:
        crit_threat = "high"
    elif ad_score == 1:
        crit_threat = "medium"
    else:
        crit_threat = "low"

    result = {
        "mix": {"ad_pct": ad_pct, "ap_pct": ap_pct},
        "tanks": tank_count,
        "cc": _severity_from_hits(cc_hits),
        "healing": _severity_from_hits(heal_shield_hits),
        "crit_threat": crit_threat,
        "poke": "medium"  
    }
    return result
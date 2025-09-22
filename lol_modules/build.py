# Para las runas, items y hechizos
from typing import Dict

def _needs_tenacity(comp: Dict) -> bool:
    return comp.get("cc") in ("high", "very_high")

def _ad_dominant(comp: Dict) -> bool:
    return comp.get("mix", {}).get("ad_pct", 0) >= 60

def _ap_sustained(comp: Dict) -> bool:
    return comp.get("mix", {}).get("ap_pct", 0) >= 40 and comp.get("cc") in ("medium", "high", "very_high")


def suggest_runes(dd, ally_champ: str, characteristic: str, comp: Dict) -> Dict:
    characteristic = characteristic.upper()
    if characteristic == "TANK":
        primary_tree = "Resolve"; keystone = "Grasp of the Undying"
        primary = ["Demolish", "Second Wind", "Overgrowth"]
        secondary_tree = "Precision"
        secondary = ["Legend: Tenacity", "Last Stand"] if _needs_tenacity(comp) else ["Triumph", "Legend: Alacrity"]
        stat_shards = ["Armor", "Health", "Health"] if _ad_dominant(comp) else ["MagicRes", "Health", "Health"]
        why = [
            "Tank characteristic: sustain and scaling HP",
            "High enemy CC → Tenacity" if _needs_tenacity(comp) else "Low enemy CC",
            "Enemy damage is AD-heavy" if _ad_dominant(comp) else "Enemy damage is mixed/AP"
        ]

    elif characteristic == "AP":
        primary_tree = "Domination"; keystone = "Electrocute"
        primary = ["Taste of Blood", "Eyeball Collection", "Ultimate Hunter"]
        secondary_tree = "Sorcery"; secondary = ["Manaflow Band", "Transcendence"]
        stat_shards = ["Adaptive", "Adaptive", "MagicRes" if _ap_sustained(comp) else "Armor"]
        why = [
            "AP burst/skirmish profile",
            "AP/CC presence → consider MR shard" if _ap_sustained(comp) else "Armor shard vs AD"
        ]

    else:  
        primary_tree = "Precision"; keystone = "Conqueror"
        primary = ["Triumph", "Legend: Tenacity" if _needs_tenacity(comp) else "Legend: Alacrity", "Last Stand"]
        secondary_tree = "Resolve"
        secondary = ["Second Wind", "Unflinching"] if _needs_tenacity(comp) else ["Bone Plating", "Overgrowth"]
        stat_shards = ["AttackSpeed", "Adaptive", "Armor" if _ad_dominant(comp) else "MagicRes"]
        why = [
            "AD sustained fighting (Conqueror)",
            "High enemy CC → Tenacity + Unflinching" if _needs_tenacity(comp) else "Lower CC → standard survivability",
            "Armor shard vs AD-heavy" if _ad_dominant(comp) else "MR shard vs AP/mixed"
        ]

    return {
        "primary_tree": primary_tree,
        "keystone": keystone,
        "primary": primary,
        "secondary_tree": secondary_tree,
        "secondary": secondary,
        "statShards": stat_shards,
        "why": [w for w in why if w]
    }


def suggest_summoners(ally_champ: str, characteristic: str, comp: Dict) -> Dict:
    characteristic = characteristic.upper()
    if characteristic == "TANK":
        return {
            "summoners": ["Flash", "Teleport"],
            "alt": ["Flash", "Ghost"],
            "why": "Tank: TP for map presence; Ghost for extended chases/escapes."
        }
    if characteristic == "AP":
        return {
            "summoners": ["Flash", "Teleport"],
            "alt": ["Flash", "Barrier"],
            "why": "AP: TP for tempo/roams; Barrier into strong burst comps."
        }
    # AD default
    return {
        "summoners": ["Flash", "Heal"],
        "alt": ["Flash", "Exhaust"],
        "why": "AD: Heal standard on carries; Exhaust vs assassins/hypercarries."
    }


def suggest_items(dd, ally_champ: str, characteristic: str, comp: Dict) -> Dict:
    characteristic = characteristic.upper()

    if characteristic == "TANK":
        starter = ["Doran's Shield", "Health Potion"]
        boots = {
            "pick": "Plated Steelcaps" if _ad_dominant(comp) else "Mercury's Treads",
            "alt": "Mercury's Treads" if _ad_dominant(comp) else "Plated Steelcaps",
            "rule": "AD-heavy → Steelcaps; otherwise Mercs vs AP/CC."
        }
        core = [
            {"item": "Sunfire Aegis", "why": "Durability + sustained AoE damage in fights."},
            {"item": "Thornmail", "why": "Apply Grievous Wounds vs healing."},
            {"item": "Randuin's Omen", "why": "Mitigate crit damage (common with AD-heavy comps)."}
        ]
        situational = [
            {"item": "Force of Nature", "when": "Sustained AP + CC (e.g., heavy magic teamfight)."},
            {"item": "Gargoyle Stoneplate", "when": "5v5 brawls and high burst."},
            {"item": "Dead Man's Plate", "when": "Need extra mobility/roam potential."}
        ]

    elif characteristic == "AP":
        starter = ["Doran's Ring", "Health Potion"]
        boots = {
            "pick": "Sorcerer's Shoes",
            "alt": "Mercury's Treads",
            "rule": "Penetration for damage; Mercs vs heavy CC/AP."
        }
        core = [
            {"item": "Luden's Companion", "why": "Burst + mana efficiency for poke/pick."},
            {"item": "Shadowflame", "why": "Great vs shields; flat pen spike."},
            {"item": "Zhonya's Hourglass", "why": "Defensive active vs engage/burst."}
        ]
        situational = [
            {"item": "Banshee's Veil", "when": "Pick-heavy or magic burst threats."},
            {"item": "Rabadon's Deathcap", "when": "Snowball/late scaling power spike."},
            {"item": "Void Staff", "when": "Enemy stacking MR."}
        ]

    else:  
        starter = ["Doran's Blade", "Health Potion"]
        boots = {
            "pick": "Berserker's Greaves",
            "alt": "Plated Steelcaps",
            "rule": "DPS default; Steelcaps vs strong enemy autos."
        }
        core = [
            {"item": "Kraken Slayer", "why": "Sustained DPS and anti-tank passive."},
            {"item": "Infinity Edge", "why": "Crit spike for carries."},
            {"item": "Lord Dominik's Regards", "why": "Armor penetration vs tanks/bruisers."}
        ]
        situational = [
            {"item": "Guardian Angel", "when": "Focused often in teamfights."},
            {"item": "Mortal Reminder", "when": "High enemy healing present."},
            {"item": "Wit's End", "when": "Sustained AP damage and need MR."}
        ]


    if comp.get("healing") in ("medium", "high", "very_high"):
        if characteristic == "AP":
            situational.insert(0, {"item": "Morellonomicon", "when": "Significant enemy healing/shields."})
        elif characteristic == "AD":
            situational.insert(0, {"item": "Mortal Reminder", "when": "Significant enemy healing."})

    return {
        "starter": starter,
        "boots": boots,
        "core": core,
        "situational": situational
    }
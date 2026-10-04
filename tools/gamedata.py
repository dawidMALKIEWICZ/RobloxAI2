"""Single source of truth for game balance. Writes src/ReplicatedStorage/Shared/GameData.json
(Rojo turns it into a ModuleScript) and is imported by the UI builder."""
import json
import os

from build_assets import CARS, STYLES
from build_track import PIECES
from rbx import SRC

TIERS = [
    {"id": "Common", "color": "#b8b8b8", "dark": "#6f6f6f"},
    {"id": "Rare", "color": "#3fa9ff", "dark": "#1d5fb3"},
    {"id": "Epic", "color": "#b54dff", "dark": "#6a1fb0"},
    {"id": "Legendary", "color": "#ffb31a", "dark": "#b36b00"},
    {"id": "Mythical", "color": "#ff3b6b", "dark": "#a3123b"},
    {"id": "Secret", "color": "#2b2b33", "dark": "#111111"},
]

PIECE_ICONS = {
    "Straight": "⬆️", "GentleCurve": "↗️", "SharpTurn": "↪️", "Ramp": "📐", "BumpyHills": "〰️",
    "BankedCurve": "🔄", "Chicane": "🐍", "Corkscrew": "🌀", "JumpGap": "🦘", "Loop": "➰",
    "BoostTunnel": "⚡", "SpiralTower": "🗼", "WaveRider": "🌊", "WallRide": "🧱",
    "TeleportGate": "🌌", "SkyLeap": "🌠",
}

POTIONS = [
    {"id": "MoneyPotion", "name": "Money Potion", "effect": "Money", "mult": 2, "duration": 300,
     "price": 2_500, "color": "#3bd16b", "icon": "💰", "desc": "x2 Money"},
    {"id": "LuckPotion", "name": "Luck Potion", "effect": "Luck", "mult": 2, "duration": 300,
     "price": 5_000, "color": "#4bdc5a", "icon": "🍀", "desc": "x2 Luck"},
    {"id": "SpeedPotion", "name": "Speed Potion", "effect": "Speed", "mult": 1.5,
     "duration": 300, "price": 1_500, "color": "#3bb8ff", "icon": "⚡", "desc": "x1.5 Car Speed"},
    {"id": "SpinPotion", "name": "Spin Potion", "effect": "Spin", "mult": 2, "duration": 300,
     "price": 3_000, "color": "#b54dff", "icon": "🌀", "desc": "x2 Spin Speed"},
]

LUCKY_BLOCKS = [
    {"id": "Lucky", "name": "Lucky Block", "price": 5_000, "luck": 5, "color": "#ffcc1a"},
    {"id": "SuperLucky", "name": "Super Lucky Block", "price": 50_000, "luck": 25,
     "color": "#3fa9ff"},
    {"id": "MegaLucky", "name": "Mega Lucky Block", "price": 500_000, "luck": 120,
     "color": "#b54dff"},
    {"id": "UltraLucky", "name": "Ultra Lucky Block", "price": 5_000_000, "luck": 600,
     "color": "#ff3b6b"},
]

# skill tree: col/row are grid coordinates in the Upgrades window
UPGRADES = [
    {"id": "Root", "name": "Engine Tune", "branch": "Money", "stat": "Money", "value": 0.10,
     "cost": 500, "requires": None, "col": 0, "row": 2, "icon": "🔧"},
]
_BR = [
    ("Money", "Money", [0.15, 0.25, 0.50, 1.00], [5_000, 75_000, 1_500_000, 40_000_000],
     ["Money I", "Money II", "Money III", "Golden Touch"], "💵", 0),
    ("Luck", "Luck", [0.20, 0.40, 0.75, 1.50], [8_000, 120_000, 2_500_000, 60_000_000],
     ["Luck I", "Luck II", "Luck III", "Four-Leaf"], "🍀", 1),
    ("Speed", "Speed", [0.10, 0.20, 0.35, 0.60], [3_000, 50_000, 1_000_000, 25_000_000],
     ["Speed I", "Speed II", "Speed III", "Nitro"], "⚡", 2),
    ("Spin", "SpinSpeed", [0.20, 0.20, 1, 0.30], [4_000, 90_000, 250_000, 10_000_000],
     ["Quick Spin I", "Quick Spin II", "Auto Spin", "Turbo Spin"], "🎰", 3),
    ("Track", "Slots", [2, 2, 2, 2], [10_000, 200_000, 4_000_000, 80_000_000],
     ["Track Slots I", "Track Slots II", "Track Slots III", "Track Slots IV"], "🛣️", 4),
]
for branch, stat, values, costs, names, icon, row in _BR:
    prev = "Root"
    for i in range(4):
        uid = f"{branch}{i + 1}"
        st = stat
        if branch == "Spin" and i == 2:
            st = "AutoSpin"
        UPGRADES.append({"id": uid, "name": names[i], "branch": branch, "stat": st,
                         "value": values[i], "cost": costs[i], "requires": prev, "col": i + 1,
                         "row": row, "icon": icon})
        prev = uid


def upgrade_desc(u):
    s, v = u["stat"], u["value"]
    if s == "Money":
        return f"+{int(v * 100)}% Money"
    if s == "Luck":
        return f"+{int(v * 100)}% Luck"
    if s == "Speed":
        return f"+{int(v * 100)}% Car Speed"
    if s == "SpinSpeed":
        return f"-{int(v * 100)}% Spin Cooldown"
    if s == "AutoSpin":
        return "Unlocks Auto Spin"
    if s == "Slots":
        return f"+{int(v)} Track Slots"
    return ""


for u in UPGRADES:
    u["desc"] = upgrade_desc(u)

DAILY = [
    {"day": 1, "type": "Cash", "amount": 1_000, "label": "$1K Cash", "icon": "💵"},
    {"day": 2, "type": "Potion", "id": "MoneyPotion", "label": "Money Potion", "icon": "💰"},
    {"day": 3, "type": "Cash", "amount": 10_000, "label": "$10K Cash", "icon": "💵"},
    {"day": 4, "type": "Potion", "id": "LuckPotion", "label": "Luck Potion", "icon": "🍀"},
    {"day": 5, "type": "Lucky", "id": "SuperLucky", "label": "Super Lucky", "icon": "🎲"},
    {"day": 6, "type": "Cash", "amount": 100_000, "label": "$100K Cash", "icon": "💰"},
    {"day": 7, "type": "Crate", "label": "Exclusive Crate", "icon": "📦"},
]

PASS_LEVELS = 20
PASS = []
for lvl in range(1, PASS_LEVELS + 1):
    if lvl % 5 == 0:
        free = {"type": "Lucky", "id": "SuperLucky" if lvl < 15 else "MegaLucky",
                "label": "Lucky Block", "icon": "🎲"}
        prem = {"type": "Crate", "label": "Exclusive Crate", "icon": "📦"} if lvl % 10 == 0 \
            else {"type": "Lucky", "id": "MegaLucky", "label": "Mega Lucky", "icon": "🎲"}
    elif lvl % 3 == 0:
        pid = ["MoneyPotion", "LuckPotion", "SpeedPotion", "SpinPotion"][lvl % 4]
        free = {"type": "Potion", "id": pid, "label": pid.replace("Potion", " Potion"),
                "icon": "🧪"}
        prem = {"type": "Potion", "id": "LuckPotion", "count": 3, "label": "3x Luck Potion",
                "icon": "🍀"}
    else:
        free = {"type": "Cash", "amount": lvl * 2_500, "label": f"${lvl * 2.5:g}K", "icon": "💵"}
        prem = {"type": "Cash", "amount": lvl * 15_000, "label": f"${lvl * 15}K", "icon": "💰"}
    PASS.append({"level": lvl, "free": free, "premium": prem})

CRATE = {
    "name": "Exclusive Track Crate",
    "drops": [
        {"piece": "Corkscrew", "chance": 50},
        {"piece": "JumpGap", "chance": 30},
        {"piece": "Loop", "chance": 15},
        {"piece": "SpiralTower", "chance": 4.99},
        {"piece": "SkyLeap", "chance": 0.01},
    ],
}

# Replace the 0 ids with real ids from Creator Dashboard. While an id is 0 the purchase is
# granted for free inside Roblox Studio only (for testing); in a live server it is disabled.
PRODUCTS = {
    "Gamepasses": {
        "X2Money": {"id": 0, "price": 9, "name": "X2 Money"},
        "X2Luck": {"id": 0, "price": 9, "name": "X2 Luck"},
        "PremiumPass": {"id": 0, "price": 99, "name": "Premium Pass"},
    },
    "DevProducts": {
        "StarterPack": {"id": 0, "price": 19, "name": "Starter Pack"},
        "Crate1": {"id": 0, "price": 29, "name": "1 Crate"},
        "Crate3": {"id": 0, "price": 55, "name": "3 Crates"},
        "Levels5": {"id": 0, "price": 49, "name": "+5 Levels"},
        "Levels10": {"id": 0, "price": 89, "name": "+10 Levels"},
        "Levels25": {"id": 0, "price": 199, "name": "+25 Levels"},
        "SkipRebirth": {"id": 0, "price": 19, "name": "Skip Rebirth"},
        "PassSkip": {"id": 0, "price": 25, "name": "Skip Pass Level"},
    },
}

STARTER_PACK = [
    {"type": "Crate", "label": "Epic Crate", "icon": "📦"},
    {"type": "Potion", "id": "MoneyPotion", "duration": 900, "label": "15 min", "icon": "💵"},
    {"type": "Potion", "id": "LuckPotion", "duration": 900, "label": "15 min", "icon": "🍀"},
    {"type": "Car", "id": "Hatchback", "label": "Hatchback", "icon": "🚗"},
]

CONFIG = {
    "BaseSlots": 6,
    "BaseSpinCooldown": 2.0,
    "XPPerSpin": 4,
    "RebirthBaseCost": 100_000,
    "RebirthCostGrowth": 5,
    "RebirthMoneyBonus": 0.3,
    "FriendBoostPer": 0.1,
    "FriendBoostMax": 0.5,
    "DailyCooldownHours": 20,
    "DailyResetHours": 48,
}


def piece_list():
    out = []
    for i, (pid, display, tier, odds, value, _b, _d, turns, desc) in enumerate(PIECES):
        out.append({"id": pid, "name": display, "tier": tier, "odds": odds, "value": value,
                    "turns": turns, "desc": desc, "icon": PIECE_ICONS[pid], "order": i + 1})
    return out


def car_list():
    return [{"id": c[0], "name": c[1], "price": c[2], "speed": c[3], "mult": c[4],
             "order": i + 1} for i, c in enumerate(CARS)]


def style_list():
    return [{"id": s[0], "name": s[1], "price": s[2], "bonus": s[3], "grass": s[4][0],
             "dirt": s[5][0], "rock": s[6][0], "order": i + 1} for i, s in enumerate(STYLES)]


def xp_for_level(lvl):
    return 100 + (lvl - 1) * 20


def data():
    return {
        "Tiers": TIERS, "Pieces": piece_list(), "Cars": car_list(), "Styles": style_list(),
        "Potions": POTIONS, "LuckyBlocks": LUCKY_BLOCKS, "Upgrades": UPGRADES, "Daily": DAILY,
        "Pass": PASS, "Crate": CRATE, "Products": PRODUCTS, "StarterPack": STARTER_PACK,
        "Config": CONFIG,
    }


if __name__ == "__main__":
    path = os.path.join(SRC, "ReplicatedStorage/Shared/GameData.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data(), f, ensure_ascii=False, indent=1)
    print("wrote", path)

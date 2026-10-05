"""Single source of truth for game balance. Writes src/ReplicatedStorage/Shared/GameData.json
(Rojo turns it into a ModuleScript) and is imported by the UI builder."""
import json
import os

from build_assets import CARS, STYLES
from build_tiles import TILES
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
    "Straight": "⬆️", "Turn": "↪️", "SpeedBump": "〰️", "Hill": "⛰️", "BankedTurn": "🔄",
    "BoostPad": "⚡", "Chicane": "🐍", "Jump": "🦘", "Corkscrew": "🌀", "Loop": "➰",
    "Spiral": "🗼", "WaveRider": "🌊", "WallRide": "🧱", "DoubleLoop": "➿",
    "TeleportGate": "🌌", "SkyLeap": "🌠", "Tunnel": "🚇", "Bridge": "🌉", "IceTurn": "🧊",
    "CamelBack": "🐫", "HalfPipe": "🛹", "NeonTurn": "💡", "RingOfFire": "🔥", "LaunchPad": "🚀",
    "Twister": "🌪️", "RainbowRoad": "🌈", "BlackHole": "🕳️", "Lift": "🛗",
}

# Every potion has its own timer key ("effect") and multiplies one or more stats while it
# runs ("boosts"). Different potions stack with each other.
POTIONS = [
    {"id": "SpeedPotion", "name": "Speed Potion", "effect": "Speed", "boosts": {"Speed": 1.5},
     "duration": 300, "price": 1_500, "color": "#3bb8ff", "icon": "⚡", "desc": "x1.5 Car Speed",
     "tier": "Common"},
    {"id": "MoneyPotion", "name": "Money Potion", "effect": "Money", "boosts": {"Money": 2},
     "duration": 300, "price": 2_500, "color": "#3bd16b", "icon": "💰", "desc": "x2 Money",
     "tier": "Common"},
    {"id": "SpinPotion", "name": "Spin Potion", "effect": "Spin", "boosts": {"Spin": 2},
     "duration": 300, "price": 3_000, "color": "#b54dff", "icon": "🌀", "desc": "x2 Roll Speed",
     "tier": "Common"},
    {"id": "LuckPotion", "name": "Luck Potion", "effect": "Luck", "boosts": {"Luck": 2},
     "duration": 300, "price": 5_000, "color": "#4bdc5a", "icon": "🍀", "desc": "x2 Luck",
     "tier": "Rare"},
    {"id": "FortunePotion", "name": "Fortune Potion", "effect": "Fortune",
     "boosts": {"Money": 1.5, "Luck": 1.5}, "duration": 600, "price": 40_000, "color": "#ffd23f",
     "icon": "🌟", "desc": "x1.5 Money & Luck", "tier": "Rare"},
    {"id": "NitroPotion", "name": "Nitro Potion", "effect": "Nitro",
     "boosts": {"Speed": 2, "Money": 1.5}, "duration": 300, "price": 90_000, "color": "#ff7b1a",
     "icon": "🔥", "desc": "x2 Speed, x1.5 Money", "tier": "Epic"},
    {"id": "MegaLuckPotion", "name": "Mega Luck", "effect": "MegaLuck", "boosts": {"Luck": 4},
     "duration": 300, "price": 150_000, "color": "#2bd96b", "icon": "☘️", "desc": "x4 Luck",
     "tier": "Epic"},
    {"id": "GoldRushPotion", "name": "Gold Rush", "effect": "GoldRush", "boosts": {"Money": 4},
     "duration": 300, "price": 250_000, "color": "#ffb31a", "icon": "🪙", "desc": "x4 Money",
     "tier": "Epic"},
    {"id": "HyperSpinPotion", "name": "Hyper Spin", "effect": "HyperSpin", "boosts": {"Spin": 3},
     "duration": 180, "price": 400_000, "color": "#d14dff", "icon": "💫", "desc": "x3 Roll Speed",
     "tier": "Legendary"},
    {"id": "RainbowElixir", "name": "Rainbow Elixir", "effect": "Rainbow",
     "boosts": {"Money": 2, "Luck": 3, "Spin": 2}, "duration": 180, "price": 2_500_000,
     "color": "rainbow", "icon": "🌈", "desc": "x2 Money, x3 Luck, x2 Roll", "tier": "Legendary"},
    {"id": "CosmicBrew", "name": "Cosmic Brew", "effect": "Cosmic", "boosts": {"Luck": 10},
     "duration": 120, "price": 10_000_000, "color": "#7b5cff", "icon": "🌌", "desc": "x10 Luck",
     "tier": "Mythical"},
    {"id": "DivineNectar", "name": "Divine Nectar", "effect": "Divine",
     "boosts": {"Money": 5, "Luck": 5, "Speed": 2, "Spin": 2}, "duration": 120,
     "price": 50_000_000, "color": "#fff3b0", "icon": "👑", "desc": "x5 Money & Luck, x2 all",
     "tier": "Secret"},
]
for _p in POTIONS:  # kept for older scripts that read a single multiplier
    _p["mult"] = max(_p["boosts"].values())

# Dice: one roll with a big luck multiplier. Price grows faster than luck, so cheaper dice
# stay worth buying early and the top dice are an end-game goal.
DICE = [
    {"id": "Golden", "name": "Golden Dice", "price": 2_500, "luck": 5, "color": "#ffcc1a",
     "color2": "#fff3b0", "tier": "Common", "vfx": 0},
    {"id": "Frost", "name": "Frost Dice", "price": 12_000, "luck": 15, "color": "#5cc8ff",
     "color2": "#e6f8ff", "tier": "Common", "vfx": 0},
    {"id": "Toxic", "name": "Toxic Dice", "price": 40_000, "luck": 35, "color": "#7dff3b",
     "color2": "#2f6b12", "tier": "Rare", "vfx": 1},
    {"id": "Inferno", "name": "Inferno Dice", "price": 120_000, "luck": 80, "color": "#ff5a1a",
     "color2": "#ffd23f", "tier": "Rare", "vfx": 1},
    {"id": "Cosmic", "name": "Cosmic Dice", "price": 300_000, "luck": 150, "color": "#b54dff",
     "color2": "#3b1f7a", "tier": "Epic", "vfx": 2},
    {"id": "Void", "name": "Void Dice", "price": 800_000, "luck": 300, "color": "#2b1640",
     "color2": "#c46bff", "tier": "Epic", "vfx": 2},
    {"id": "Cyber", "name": "Cyber Dice", "price": 2_000_000, "luck": 600, "color": "#14e0ff",
     "color2": "#0d1a33", "tier": "Legendary", "vfx": 3},
    {"id": "Rainbow", "name": "Rainbow Dice", "price": 5_000_000, "luck": 1_200,
     "color": "rainbow", "color2": "#ffffff", "tier": "Legendary", "vfx": 3},
    {"id": "Galaxy", "name": "Galaxy Dice", "price": 12_000_000, "luck": 2_500,
     "color": "#3b4dff", "color2": "#ff6fd8", "tier": "Mythical", "vfx": 4},
    {"id": "Glitch", "name": "Glitch Dice", "price": 30_000_000, "luck": 5_000,
     "color": "#ff2bd6", "color2": "#2bff8a", "tier": "Mythical", "vfx": 4},
    {"id": "Celestial", "name": "Celestial Dice", "price": 75_000_000, "luck": 10_000,
     "color": "#fff6d6", "color2": "#8fe3ff", "tier": "Secret", "vfx": 5},
    {"id": "Divine", "name": "Divine Dice", "price": 200_000_000, "luck": 25_000,
     "color": "#ffd23f", "color2": "#ffffff", "tier": "Secret", "vfx": 5},
    {"id": "Singularity", "name": "Singularity Dice", "price": 500_000_000, "luck": 60_000,
     "color": "#0a0a12", "color2": "#ffb31a", "tier": "Secret", "vfx": 5},
]

# Track mutations: every rolled piece may come out mutated. A mutated copy earns `mult` times
# more and gets its own look (a recoloured palette texture + effects). `chance` = 1 in N at
# luck 1; luck raises it gently (see Stats.rollMutation). Ordered common -> rare.
MUTATIONS = [
    {"id": "Golden", "name": "Golden", "mult": 1.5, "chance": 12, "color": "#ffcc33",
     "color2": "#fff3b0", "glow": "#ffd23f"},
    {"id": "Frozen", "name": "Frozen", "mult": 2, "chance": 30, "color": "#7fd8ff",
     "color2": "#eefbff", "glow": "#9fe8ff"},
    {"id": "Diamond", "name": "Diamond", "mult": 3, "chance": 80, "color": "#b9f6ff",
     "color2": "#ffffff", "glow": "#d9fbff"},
    {"id": "Neon", "name": "Neon", "mult": 4, "chance": 200, "color": "#ff3bd4",
     "color2": "#3bf6ff", "glow": "#ff3bd4"},
    {"id": "Rainbow", "name": "Rainbow", "mult": 6, "chance": 600, "color": "rainbow",
     "color2": "#ffffff", "glow": "#ffffff"},
    {"id": "Void", "name": "Void", "mult": 10, "chance": 2000, "color": "#8a3bff",
     "color2": "#1a0833", "glow": "#b46bff"},
]

# skill tree: col/row are grid coordinates in the Skills window
UPGRADES = [
    {"id": "Root", "name": "Engine Tune", "branch": "Money", "stat": "Money", "value": 0.10,
     "cost": 100, "requires": None, "col": 0, "row": 3, "icon": "🔧"},
]
_BR = [
    ("Money", "Money", [0.25, 0.5, 1.0, 2.0], [1_500, 40_000, 900_000, 25_000_000],
     ["Money I", "Money II", "Money III", "Golden Touch"], "💵", 0),
    ("Luck", "Luck", [0.25, 0.5, 1.0, 2.0], [2_500, 60_000, 1_500_000, 40_000_000],
     ["Luck I", "Luck II", "Luck III", "Four-Leaf"], "🍀", 1),
    ("Speed", "Speed", [0.15, 0.3, 0.5, 0.8], [1_000, 25_000, 600_000, 15_000_000],
     ["Speed I", "Speed II", "Speed III", "Nitro"], "⚡", 2),
    ("Roll", "RollSpeed", [0.2, 0.2, 0.2, 0.3], [1_200, 30_000, 120_000, 8_000_000],
     ["Quick Roll I", "Quick Roll II", "Quick Roll III", "Turbo Roll"], "🎲", 4),
    ("Plot", "PlotSize", [9, 11, 13, 15], [5_000, 150_000, 3_000_000, 60_000_000],
     ["Plot 9x9", "Plot 11x11", "Plot 13x13", "Plot 15x15"], "🗺️", 5),
]
for branch, stat, values, costs, names, icon, row in _BR:
    prev = "Root"
    for i in range(4):
        uid = f"{branch}{i + 1}"
        UPGRADES.append({"id": uid, "name": names[i], "branch": branch, "stat": stat,
                         "value": values[i], "cost": costs[i], "requires": prev, "col": i + 1,
                         "row": row, "icon": icon})
        prev = uid
# elements: 8 nodes, +20 each (30 -> 190), laid out in two rows of four
_EL_COSTS = [800, 6_000, 40_000, 250_000, 1_500_000, 9_000_000, 50_000_000, 250_000_000]
prev = "Root"
for i, c in enumerate(_EL_COSTS):
    uid = f"Elements{i + 1}"
    UPGRADES.append({"id": uid, "name": f"Elements +20 ({30 + 20 * (i + 1)})", "branch": "Elements",
                     "stat": "Elements", "value": 20, "cost": c, "requires": prev,
                     "col": 1 + (i % 4) + (4 if i >= 4 else 0), "row": 3, "icon": "🧱"})
    prev = uid


def upgrade_desc(u):
    s, v = u["stat"], u["value"]
    if s == "Money":
        return f"+{int(v * 100)}% Money"
    if s == "Luck":
        return f"+{int(v * 100)}% Luck"
    if s == "Speed":
        return f"+{int(v * 100)}% Car Speed"
    if s == "RollSpeed":
        return f"-{int(v * 100)}% Roll Time"
    if s == "AutoRoll":
        return "Unlocks Auto Roll"
    if s == "PlotSize":
        return f"Plot grows to {int(v)}x{int(v)}"
    if s == "Elements":
        return f"+{int(v)} max track elements"
    return ""


for u in UPGRADES:
    u["desc"] = upgrade_desc(u)

DAILY = [
    {"day": 1, "type": "Cash", "amount": 1_000, "label": "$1K Cash", "icon": "💵"},
    {"day": 2, "type": "Potion", "id": "MoneyPotion", "label": "Money Potion", "icon": "💰"},
    {"day": 3, "type": "Cash", "amount": 10_000, "label": "$10K Cash", "icon": "💵"},
    {"day": 4, "type": "Potion", "id": "LuckPotion", "label": "Luck Potion", "icon": "🍀"},
    {"day": 5, "type": "Dice", "id": "Frost", "label": "Frost Dice", "icon": "🎲"},
    {"day": 6, "type": "Cash", "amount": 100_000, "label": "$100K Cash", "icon": "💰"},
    {"day": 7, "type": "Crate", "label": "Exclusive Crate", "icon": "📦"},
]

PASS_LEVELS = 20
PASS = []
for lvl in range(1, PASS_LEVELS + 1):
    if lvl % 5 == 0:
        free = {"type": "Dice", "id": "Frost" if lvl < 15 else "Cosmic",
                "label": "Frost Dice" if lvl < 15 else "Cosmic Dice", "icon": "🎲"}
        prem = {"type": "Crate", "label": "Exclusive Crate", "icon": "📦"} if lvl % 10 == 0 \
            else {"type": "Dice", "id": "Cosmic", "label": "Cosmic Dice", "icon": "🎲"}
    elif lvl % 3 == 0:
        pid = ["MoneyPotion", "LuckPotion", "SpeedPotion", "SpinPotion"][lvl % 4]
        free = {"type": "Potion", "id": pid, "label": pid.replace("Potion", " Potion"),
                "icon": "🧪"}
        prem = {"type": "Potion", "id": "LuckPotion", "count": 3, "label": "3x Luck Potion",
                "icon": "🍀"}
    else:
        free = {"type": "Cash", "amount": lvl * 1_000, "label": f"${lvl}K", "icon": "💵"}
        prem = {"type": "Cash", "amount": lvl * 6_000, "label": f"${lvl * 6}K", "icon": "💰"}
    PASS.append({"level": lvl, "free": free, "premium": prem})

CRATE = {
    "name": "Exclusive Track Crate",
    "drops": [
        {"piece": "Jump", "chance": 50},
        {"piece": "Corkscrew", "chance": 30},
        {"piece": "Loop", "chance": 15},
        {"piece": "Spiral", "chance": 4.99},
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
        "PassSkip": {"id": 0, "price": 25, "name": "Skip Pass Level"},
    },
}

STARTER_PACK = [
    {"type": "Crate", "label": "Epic Crate", "icon": "📦"},
    {"type": "Potion", "id": "MoneyPotion", "duration": 900, "label": "15 min", "icon": "💵"},
    {"type": "Potion", "id": "LuckPotion", "duration": 900, "label": "15 min", "icon": "🍀"},
    {"type": "Car", "id": "Hatchback", "label": "Hatchback", "icon": "🚗"},
    {"type": "Dice", "id": "Cosmic", "label": "Cosmic Dice", "icon": "🎲"},
]

CONFIG = {
    "BaseElements": 30,
    "BaseGrid": 7,
    "MaxGrid": 15,
    "Cell": 10,
    "BaseRollTime": 2.0,
    "XPPerRoll": 4,
    "FriendBoostPer": 0.1,
    "FriendBoostMax": 0.5,
    "DailyCooldownHours": 20,
    "DailyResetHours": 48,
    "OfflineRate": 0.25,
    "OfflineMaxHours": 8,
    "StartInventory": {"Straight": 8, "Turn": 4},
    "FloorHeight": 9,
    "SecondFloorPrice": 100_000,
    "SecondFloorLifts": 2,      # free Sky Ramps when the 2nd floor is bought
    "FuseCount": 3,             # dice of one kind fused into one die of the next kind
    "FuseJackpot": 0.1,         # chance the fusion skips a tier
    "MutationLuckPower": 0.35,  # luck^power multiplies mutation chances
}


def tile_heights():
    """Top of every baked tile above the pad (studs), from the mesh manifest."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets",
                     "meshes", "manifest.json")
    man = json.load(open(p)) if os.path.exists(p) else {}
    out = {}
    for k, v in man.items():
        if k.startswith("Tile_") and v:
            out[k[5:]] = round(max(e["center"][1] + e["size"][1] / 2 for e in v), 2)
    return out


def piece_list():
    heights = tile_heights()
    out = []
    for i, (pid, display, tier, odds, value, _f, _d, ports, desc) in enumerate(TILES):
        out.append({"id": pid, "name": display, "tier": tier, "odds": odds, "value": value,
                    "ports": ports, "desc": desc, "icon": PIECE_ICONS[pid], "order": i + 1,
                    "height": heights.get(pid, 10.4 if pid == "Lift" else 3.0),
                    "lift": pid == "Lift"})
    return out


def mutation_list():
    tex = media().get("mutations", {})
    out = []
    for i, m in enumerate(MUTATIONS):
        m = dict(m, order=i + 1)
        if tex.get(m["id"]):
            m["texture"] = f"rbxassetid://{tex[m['id']]}"
        out.append(m)
    return out


def car_list():
    return [{"id": c[0], "name": c[1], "price": c[2], "speed": c[3], "mult": c[4],
             "order": i + 1} for i, c in enumerate(CARS)]


def style_list():
    return [{"id": s[0], "name": s[1], "price": s[2], "bonus": s[3], "grass": s[4][0],
             "dirt": s[5][0], "rock": s[6][0], "order": i + 1} for i, s in enumerate(STYLES)]


def xp_for_level(lvl):
    return 100 + (lvl - 1) * 20


def media():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media_ids.json")
    return json.load(open(p)) if os.path.exists(p) else {"icons": {}, "audio": {}}


def with_icons(items, prefix):
    icons = media()["icons"]
    out = []
    for it in items:
        it = dict(it)
        aid = icons.get(prefix + it["id"])
        if aid:
            it["image"] = f"rbxassetid://{aid}"
        out.append(it)
    return out


def audio():
    return {k: f"rbxassetid://{v}" for k, v in media()["audio"].items()}


def ui_art():
    return {k: f"rbxassetid://{v}" for k, v in media().get("ui", {}).items()}


def fx():
    return {k: f"rbxassetid://{v}" for k, v in media().get("fx", {}).items()}


def data():
    return {
        "Tiers": TIERS, "Pieces": piece_list(), "Cars": car_list(), "Styles": style_list(),
        "Potions": with_icons(POTIONS, "Potion_"), "Dice": with_icons(DICE, "Dice_"),
        "Audio": audio(), "FX": fx(), "UIArt": ui_art(), "Upgrades": UPGRADES, "Daily": DAILY,
        "Pass": PASS, "Crate": CRATE, "Products": PRODUCTS, "StarterPack": STARTER_PACK,
        "Config": CONFIG, "Mutations": mutation_list(),
    }


if __name__ == "__main__":
    path = os.path.join(SRC, "ReplicatedStorage/Shared/GameData.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data(), f, ensure_ascii=False, indent=1)
    print("wrote", path)

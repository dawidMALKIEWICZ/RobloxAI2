"""Builds the whole game UI as static Roblox instances (src/StarterGui/MainGui.model.json).

Layout is authored for a 1920x1080 reference screen; a UIScale on the root is adjusted by
the client so it fits any screen. Names here are the contract with the client script.
"""
import math

from gamedata import (CRATE, DAILY, LUCKY_BLOCKS, PASS, POTIONS, PRODUCTS, STARTER_PACK, TIERS,
                      UPGRADES, car_list, piece_list, style_list)
from rbx import C3, CS, FONT, Inst, NS, U2, UD, V2, write_model

OUTLINE = "#15131f"
ROBUX = ""
PRESETS = {
    "green": ("#c9ff7a", "#62e026", "#2c9c10"),
    "red": ("#ff9aa5", "#ff3d5e", "#c3112f"),
    "pink": ("#ffb0d8", "#ff4fa3", "#c41f6e"),
    "blue": ("#a6e9ff", "#33aaff", "#1563c9"),
    "yellow": ("#fff59a", "#ffc61a", "#e58a00"),
    "orange": ("#ffd29a", "#ff9420", "#cc5a00"),
    "purple": ("#e6b3ff", "#a94dff", "#6a1fc9"),
    "gray": ("#eeeeee", "#a9a9b3", "#6d6d78"),
    "dark": ("#3c4868", "#28314d", "#1a2036"),
    "body": ("#2f3a5c", "#252e4a", "#1c2340"),
    "gold": ("#fff3a6", "#ffcf33", "#d68f00"),
    "cyan": ("#b3fbff", "#28d9e6", "#0f8f99"),
    "rainbow": None,
}
TIER_COL = {t["id"]: (t["color"], t["dark"]) for t in TIERS}


# ------------------------------------------------------------------ primitives
def gradient(preset, rotation=90):
    if preset == "rainbow":
        return Inst("UIGradient", "Gradient", {
            "Color": CS((0, "#ff4b4b"), (0.2, "#ffb31a"), (0.4, "#ffe03b"), (0.6, "#4bdc5a"),
                        (0.8, "#3bb8ff"), (1, "#b54dff")), "Rotation": 20})
    lt, base, dk = PRESETS[preset]
    return Inst("UIGradient", "Gradient", {
        "Color": CS((0, lt), (0.42, base), (0.58, base), (1, dk)), "Rotation": rotation})


def corner(r):
    return Inst("UICorner", "Corner", {"CornerRadius": UD(0, r)})


def stroke(th=4, color=OUTLINE, border=True, transp=0):
    p = {"Thickness": th, "Color": C3(color), "LineJoinMode": "Round"}
    if border:
        p["ApplyStrokeMode"] = "Border"
    if transp:
        p["Transparency"] = transp
    return Inst("UIStroke", "Stroke", p)


def base_props(pos, size, anchor=(0, 0), visible=True, z=None):
    p = {"Position": U2(*pos), "Size": U2(*size), "AnchorPoint": V2(*anchor),
         "BorderSizePixel": 0}
    if not visible:
        p["Visible"] = False
    if z is not None:
        p["ZIndex"] = z
    return p


def frame(name, pos, size, color=None, preset=None, rad=14, st=4, anchor=(0, 0), transp=0.0,
          visible=True, z=None, cls="Frame", st_color=OUTLINE, clip=False):
    p = base_props(pos, size, anchor, visible, z)
    if color is None and preset is None:
        p["BackgroundTransparency"] = 1
    else:
        p["BackgroundColor3"] = C3("#ffffff" if preset else color)
        if transp:
            p["BackgroundTransparency"] = transp
    if clip:
        p["ClipsDescendants"] = True
    f = Inst(cls, name, p)
    if preset:
        f.add(gradient(preset))
    if rad:
        f.add(corner(rad))
    if st:
        f.add(stroke(st, st_color))
    return f


def label(name, text, pos, size, ts=32, color="#ffffff", st=3, align="Center", anchor=(0, 0),
          font="Fredoka", valign="Center", z=None, wrap=False, scaled=False, st_color=OUTLINE,
          visible=True):
    p = base_props(pos, size, anchor, visible, z)
    p.update({"BackgroundTransparency": 1, "Text": text, "TextSize": ts, "FontFace": FONT(font),
              "TextColor3": C3(color), "TextXAlignment": align, "TextYAlignment": valign})
    if wrap:
        p["TextWrapped"] = True
    if scaled:
        p["TextScaled"] = True
    lb = Inst("TextLabel", name, p)
    if st:
        lb.add(Inst("UIStroke", "Stroke", {"Thickness": st, "Color": C3(st_color),
                                          "LineJoinMode": "Round"}))
    return lb


def button(name, text, pos, size, preset="green", ts=36, anchor=(0, 0), rad=12, st=4,
           icon=None, icon_ts=None, sub=None, visible=True, z=None, text_color="#ffffff"):
    p = base_props(pos, size, anchor, visible, z)
    p.update({"BackgroundColor3": C3("#ffffff"), "Text": "", "AutoButtonColor": False})
    b = Inst("TextButton", name, p)
    if preset:
        b.add(gradient(preset))
    b.add(corner(rad))
    b.add(stroke(st))
    w, h = size[1], size[3]
    if icon:
        its = icon_ts or int(h * 0.6)
        b.add(label("Icon", icon, (0, 0, 0, 0), (0, h, 1, 0), its, st=0))
        b.add(label("Label", text, (0, h - 6, 0, 0), (1, -h, 1, 0), ts, text_color))
    elif sub:
        b.add(label("Label", text, (0, 0, 0, 2), (1, 0, 0.62, 0), ts, text_color))
        b.add(label("Sub", sub, (0, 0, 0.58, 0), (1, 0, 0.36, 0), int(ts * 0.48), text_color,
                    st=2))
    else:
        b.add(label("Label", text, (0, 0, 0, 0), (1, 0, 1, 0), ts, text_color))
    return b


def emoji(name, ch, pos, size, ts, anchor=(0, 0), z=None):
    return label(name, ch, pos, size, ts, st=0, anchor=anchor, z=z)


def bar(name, pos, size, fill=0.57, preset_fill="orange", anchor=(0, 0), text=None, ts=26):
    b = frame(name, pos, size, color="#1c2236", rad=10, st=4, anchor=anchor)
    f = frame("Fill", (0, 0, 0, 0), (fill, 0, 1, 0), preset=preset_fill, rad=10, st=0)
    b.add(f)
    if text is not None:
        b.add(label("Text", text, (0, 0, 0, 0), (1, 0, 1, 0), ts))
    return b


def robux(n):
    return f"{ROBUX}{n}"


def short(n):
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            v = n / div
            return f"${v:.3g}{suf}"
    return f"${n:,}"


def window(name, title, icon, preset, w, h, extra_right=0):
    root = frame(name, (0.5, 0, 0.5, 10), (0, w, 0, h), anchor=(0.5, 0.5), st=0, rad=0,
                 visible=False)
    body = frame("Body", (0, 0, 0, 84), (1, 0, 1, -84), preset="body", rad=16, st=5)
    root.add(body)
    head = frame("Header", (0, -8, 0, 0), (1, 16, 0, 100), preset=preset, rad=16, st=5)
    # diagonal shine stripes for the glossy look
    head.add(frame("Shine", (0, 0, 0, 0), (1, 0, 0.45, 0), color="#ffffff", transp=0.82, rad=14,
                   st=0))
    head.add(emoji("Icon", icon, (0, 10, 0.5, 0), (0, 96, 0, 96), 66, anchor=(0, 0.5)))
    head.add(label("Title", title, (0, 112, 0, 0), (0.6, 0, 1, 0), 64, align="Left", st=5))
    head.add(button("Close", "X", (1, -14, 0.5, 0), (0, 78, 0, 74), "red", 48, anchor=(1, 0.5)))
    root.add(head)
    return root, body


# ------------------------------------------------------------------ HUD
def hud():
    h = frame("HUD", (0, 0, 0, 0), (1, 0, 1, 0), st=0, rad=0)
    # top tabs
    top = frame("TopBar", (0.5, 0, 0, 0), (0, 900, 0, 120), anchor=(0.5, 0), st=0, rad=0)
    top.add(button("ShopTab", "Shop", (0.5, -178, 0, 6), (0, 254, 0, 88), "pink", 52,
                   anchor=(1, 0)))
    top.add(button("BaseTab", "My Base", (0.5, 0, 0, 0), (0, 336, 0, 108), "blue", 62,
                   anchor=(0.5, 0)))
    top.add(button("UpgradesTab", "Upgrades", (0.5, 178, 0, 6), (0, 262, 0, 88), "green", 48))
    h.add(top)

    # left menu
    left = frame("LeftMenu", (0, 24, 0.5, -230), (0, 350, 0, 520), st=0, rad=0)
    d = button("DailyButton", "Daily Rewards", (0, 0, 0, 0), (0, 342, 0, 92), "green", 40)
    badge = frame("Badge", (1, -12, 0, -14), (0, 42, 0, 42), color="#ff2d3d", rad=21, st=4)
    badge.add(label("Text", "!", (0, 0, 0, 0), (1, 0, 1, 0), 32, st=2))
    d.add(badge)
    left.add(d)
    sq = [("ShopButton", "Shop", "pink", "🛒"), ("PassButton", "Pass", "yellow", "🎟️"),
          ("RebirthButton", "Rebirth", "purple", "🔄"), ("IndexButton", "Index", "blue", "📘")]
    for i, (n, t, pr, ic) in enumerate(sq):
        x = (i % 2) * 176
        y = 110 + (i // 2) * 176
        b = button(n, "", (0, x, 0, y), (0, 166, 0, 166), pr, 1)
        b.children = [c for c in b.children if c.name != "Label"]
        b.add(emoji("Icon", ic, (0.5, 0, 0, 6), (0, 120, 0, 110), 84, anchor=(0.5, 0)))
        b.add(label("Label", t, (0, 0, 1, -54), (1, 0, 0, 50), 40))
        left.add(b)
    h.add(left)

    # right menu
    right = frame("RightMenu", (1, -20, 0.5, -300), (0, 250, 0, 470), anchor=(1, 0), st=0, rad=0)
    sp = Inst("TextButton", "StarterPackButton", {
        **base_props((0.5, 0, 0, 0), (0, 200, 0, 220), (0.5, 0)), "BackgroundTransparency": 1,
        "Text": "", "AutoButtonColor": False})
    sp.add(label("Title", "Starter Pack", (0, 0, 0, 0), (1, 0, 0, 40), 30))
    sp.add(emoji("Icon", "🎁", (0.5, 0, 0, 34), (0, 140, 0, 140), 112, anchor=(0.5, 0)))
    sp.add(label("Price", robux(PRODUCTS["DevProducts"]["StarterPack"]["price"]),
                 (0, 0, 0, 172), (1, 0, 0, 44), 36, color="#7dff6b"))
    right.add(sp)
    right.add(button("X2MoneyButton", "X2 Money", (0.5, 0, 0, 236), (0, 246, 0, 92), "purple",
                     40, anchor=(0.5, 0), sub=robux(PRODUCTS["Gamepasses"]["X2Money"]["price"])))
    right.add(button("X2LuckButton", "X2 Luck", (0.5, 0, 0, 342), (0, 246, 0, 92), "purple", 40,
                     anchor=(0.5, 0), sub=robux(PRODUCTS["Gamepasses"]["X2Luck"]["price"])))
    h.add(right)

    # bottom-left stats
    st = frame("Stats", (0, 24, 1, -20), (0, 520, 0, 190), anchor=(0, 1), st=0, rad=0)
    st.add(emoji("RebirthIcon", "🔄", (0, 0, 0, 0), (0, 56, 0, 56), 44))
    st.add(label("RebirthCount", "0", (0, 62, 0, 0), (0, 200, 0, 56), 46, color="#ff6b8a",
                 align="Left"))
    row = frame("MoneyRow", (0, 0, 0, 58), (0, 520, 0, 84), st=0, rad=0)
    row.add(Inst("UIListLayout", "Layout", {"FillDirection": "Horizontal",
                                            "VerticalAlignment": "Center", "Padding": UD(0, 14),
                                            "SortOrder": "LayoutOrder"}))
    money = label("Money", "$0", (0, 0, 0, 0), (0, 0, 1, 0), 76, color="#7dff4f", align="Left",
                  st=5)
    money.props["AutomaticSize"] = "X"
    money.props["LayoutOrder"] = 1
    row.add(money)
    add_btn = button("AddMoneyButton", "+", (0, 0, 0, 0), (0, 62, 0, 62), "green", 50, rad=10)
    add_btn.props["LayoutOrder"] = 2
    row.add(add_btn)
    st.add(row)
    st.add(label("FriendBoost", "Friend Boost: +0%", (0, 0, 0, 144), (0, 420, 0, 42), 32,
                 align="Left"))
    h.add(st)

    # bottom-centre level bar
    lv = frame("LevelBar", (0.5, 0, 1, -16), (0, 800, 0, 172), anchor=(0.5, 1), st=0, rad=0)
    lv.add(label("Multiplier", "x1 Multiplier", (1, 0, 0, 0), (0, 320, 0, 38), 32,
                 color="#ffe14d", align="Right", anchor=(1, 0)))
    b = bar("Bar", (0, 0, 0, 40), (1, 0, 0, 58), 0.0)
    b.add(label("LevelText", "Level 1", (0, 18, 0, 0), (0.5, 0, 1, 0), 36, align="Left"))
    b.add(label("XPText", "0/100 XP", (0.5, 0, 0, 0), (0.5, -18, 1, 0), 34, align="Right"))
    lv.add(b)
    for i, (n, t, col) in enumerate([("Levels5", "+5 Levels", "#ffffff"),
                                     ("Levels10", "+10 Levels", "#ffffff"),
                                     ("Levels25", "+25 Levels", "#ffffff")]):
        lv.add(button(n, t, (0, i * 272, 0, 108), (0, 256, 0, 64), "green", 36))
    h.add(lv)

    # bottom-right boosts
    bo = frame("Boosts", (1, -20, 1, -16), (0, 300, 0, 96), anchor=(1, 1), st=0, rad=0)
    for i, (n, ic, v) in enumerate([("MoneyBoost", "💵", "x1"), ("RebirthBoost", "🔄", "x1"),
                                    ("LuckBoost", "🍀", "x1")]):
        f = frame(n, (0, i * 100, 0, 0), (0, 92, 0, 92), st=0, rad=0)
        f.add(emoji("Icon", ic, (0.5, 0, 0, 0), (0, 70, 0, 64), 52, anchor=(0.5, 0)))
        f.add(label("Value", v, (0, 0, 1, -32), (1, 0, 0, 32), 28))
        bo.add(f)
    h.add(bo)

    # spin panel (game specific)
    spn = frame("SpinPanel", (1, -24, 1, -112), (0, 470, 0, 214), anchor=(1, 1), st=0, rad=0)
    spn.add(label("LuckLabel", "🍀 Luck x1", (1, 0, 0, 0), (0, 300, 0, 40), 32, color="#9dff7a",
                  align="Right", anchor=(1, 0)))
    spn.add(label("SlotsLabel", "Track 0/6", (0, 0, 0, 0), (0, 160, 0, 40), 30, align="Left"))
    sb = button("SpinButton", "SPIN!", (1, 0, 0, 46), (0, 300, 0, 134), "gold", 78,
                anchor=(1, 0), rad=18, st=6)
    sb.add(frame("Cooldown", (0, 0, 1, 0), (1, 0, 0, 0), color="#000000", transp=0.55, rad=18,
                 st=0, anchor=(0, 1)))
    spn.add(sb)
    spn.add(button("AutoButton", "AUTO", (0, 0, 0, 74), (0, 150, 0, 78), "gray", 40,
                   sub="OFF"))
    spn.add(bar("CooldownBar", (1, 0, 0, 188), (0, 300, 0, 24), 1.0, "yellow", anchor=(1, 0)))
    h.add(spn)

    # active potion timers (filled by client from template)
    pot = frame("ActivePotions", (0, 24, 0, 180), (0, 400, 0, 120), st=0, rad=0)
    pot.add(Inst("UIListLayout", "Layout", {"FillDirection": "Horizontal",
                                            "Padding": UD(0, 10), "SortOrder": "LayoutOrder"}))
    h.add(pot)
    return h


# ------------------------------------------------------------------ windows
def crate_icon(name, pos, size, ts, anchor=(0, 0), color="#ffffff"):
    return emoji(name, "📦", pos, size, ts, anchor)


def shop_window():
    w, h = 1000, 720
    root, body = window("ShopWindow", "Shop", "🛒", "pink", w, h)
    # crate card
    c = frame("CrateCard", (0, 18, 0, 34), (1, -36, 0, 316), preset="rainbow", rad=14, st=5)
    c.add(frame("Dim", (0, 0, 0, 0), (1, 0, 1, 0), color="#000000", transp=0.72, rad=14, st=0))
    c.add(frame("IconBox", (0, 18, 0, 22), (0, 200, 0, 196), color="#ffffff", transp=0.85,
                rad=14, st=0))
    c.add(crate_icon("Icon", (0, 118, 0, 120), (0, 190, 0, 190), 140, anchor=(0.5, 0.5)))
    c.add(label("Name1", "Exclusive", (0, 18, 0, 222), (0, 200, 0, 40), 34, color="#ffb31a"))
    c.add(label("Name2", "Track Crate", (0, 18, 0, 258), (0, 200, 0, 40), 32))
    c.add(label("Equals", "=", (0, 222, 0, 90), (0, 60, 0, 80), 80))
    c.add(label("Title", "Exclusive Track Crate!", (0, 290, 0, 8), (0, 640, 0, 60), 48))
    pieces = {p["id"]: p for p in piece_list()}
    for i, d in enumerate(CRATE["drops"]):
        p = pieces[d["piece"]]
        col, dk = TIER_COL[p["tier"]]
        x = 296 + i * 128
        s = frame(f"Drop{i + 1}", (0, x, 0, 74), (0, 116, 0, 128), color=col, rad=10, st=4)
        s.add(gradient("rainbow" if p["tier"] == "Secret" else "gray"))
        s.children[-1].props["Rotation"] = 90
        s.add(frame("Tint", (0, 0, 0, 0), (1, 0, 1, 0), color=col, transp=0.25, rad=10, st=0))
        s.add(label("Chance", f"{d['chance']:g}%", (0, 0, 0, 2), (1, 0, 0, 30), 26))
        s.add(emoji("Icon", p["icon"], (0.5, 0, 0, 30), (0, 64, 0, 60), 46, anchor=(0.5, 0)))
        s.add(label("Name", p["name"], (0, 2, 1, -34), (1, -4, 0, 32), 20, scaled=True))
        c.add(s)
    c.add(button("Buy3Button", robux(PRODUCTS["DevProducts"]["Crate3"]["price"]),
                 (0, 300, 0, 222), (0, 300, 0, 80), "purple", 46, sub="3 Crates"))
    c.add(button("Buy1Button", robux(PRODUCTS["DevProducts"]["Crate1"]["price"]),
                 (0, 620, 0, 222), (0, 300, 0, 80), "green", 46, sub="1 Crate"))
    body.add(c)
    # starter pack card
    s = frame("StarterCard", (0, 18, 0, 366), (1, -36, 0, 240), preset="purple", rad=14, st=5)
    s.add(frame("Dim", (0, 0, 0, 0), (1, 0, 1, 0), color="#2a0f4f", transp=0.45, rad=14, st=0))
    s.add(label("Title", "Limited Starter Pack!", (0, 280, 0, 8), (0, 560, 0, 56), 46))
    s.add(crate_icon("Icon", (0, 110, 0, 104), (0, 150, 0, 150), 116, anchor=(0.5, 0.5)))
    s.add(label("Name1", "Epic", (0, 18, 0, 176), (0, 190, 0, 30), 30, color="#d9a3ff"))
    s.add(label("Name2", "Track Crate", (0, 18, 0, 202), (0, 190, 0, 30), 26))
    s.add(label("Plus", "+", (0, 206, 0, 80), (0, 60, 0, 70), 72))
    for i, it in enumerate(STARTER_PACK[1:]):
        x = 280 + i * 140
        f = frame(f"Item{i + 1}", (0, x, 0, 70), (0, 126, 0, 150), preset="dark", rad=10, st=4)
        f.add(label("Count", "x1", (0, 0, 0, 0), (1, 0, 0, 30), 26))
        f.add(emoji("Icon", it["icon"], (0.5, 0, 0, 28), (0, 70, 0, 66), 52, anchor=(0.5, 0)))
        f.add(label("Name", it["label"], (0, 2, 1, -38), (1, -4, 0, 34), 24))
        s.add(f)
    s.add(label("Value", "VALUE!", (0, 720, 0, 70), (0, 220, 0, 50), 44, color="#ffe14d"))
    s.add(button("BuyButton", robux(PRODUCTS["DevProducts"]["StarterPack"]["price"]),
                 (0, 712, 0, 124), (0, 230, 0, 88), "green", 54))
    s.add(label("Owned", "OWNED", (0, 712, 0, 124), (0, 230, 0, 88), 50, color="#9dff7a",
                visible=False))
    body.add(s)
    return root


def daily_window():
    w, h = 1176, 690
    root, body = window("DailyWindow", "Daily Rewards", "📅", "blue", w, h)
    root.children[1].add(button("ClaimAllButton", "CLAIM ALL", (1, -104, 0.5, 0),
                                (0, 250, 0, 70), "yellow", 40, anchor=(1, 0.5)))
    cols = {1: "blue", 2: "blue", 3: "blue", 4: "purple", 5: "purple", 6: "yellow"}
    for d in DAILY:
        n = d["day"]
        if n < 7:
            i = n - 1
            x = 22 + (i % 3) * 282
            y = 34 + (i // 3) * 288
            cw, ch = 266, 272
            pr = cols[n]
        else:
            x, y, cw, ch, pr = 22 + 3 * 282, 34, 288, 560, "rainbow"
        c = frame(f"Day{n}", (0, x, 0, y), (0, cw, 0, ch), preset=pr, rad=14, st=5)
        c.add(frame("Shine", (0, 0, 0, 0), (1, 0, 0.4, 0), color="#ffffff", transp=0.85, rad=14,
                    st=0))
        c.add(label("Title", f"DAY {n}", (0, 0, 0, 6), (1, 0, 0, 56), 54 if n < 7 else 66))
        big = n == 7
        c.add(emoji("Icon", d["icon"], (0.5, 0, 0, 62 if not big else 150),
                    (0, 120, 0, 110) if not big else (0, 200, 0, 190), 84 if not big else 150,
                    anchor=(0.5, 0)))
        c.add(label("Reward", d["label"] + "!", (0, 4, 1, -120 if not big else -190),
                    (1, -8, 0, 40 if not big else 100), 32 if not big else 46, wrap=big))
        c.add(button("Status", "LOCKED", (0.5, 0, 1, -12), (0, 220, 0, 66), "red", 38,
                     anchor=(0.5, 1)))
        if big:
            op = label("OP", "OP", (1, 18, 0, -26), (0, 90, 0, 60), 50, color="#ff3b6b",
                       anchor=(1, 0), st=4)
            op.props["Rotation"] = 20
            c.add(op)
        body.add(c)
    body.add(label("Timer", "Next reward in --:--:--", (0, 0, 1, 12), (1, 0, 0, 40), 32,
                   color="#ffffff"))
    return root


def piece_card(p, size=190):
    col, dk = TIER_COL[p["tier"]]
    c = Inst("TextButton", f"Piece_{p['id']}", {
        **base_props((0, 0, 0, 0), (0, size, 0, size)), "BackgroundColor3": C3("#1d2233"),
        "Text": "", "AutoButtonColor": False, "LayoutOrder": p["order"]})
    c.add(corner(12))
    c.add(stroke(4))
    glow = Inst("ImageLabel", "Glow", {**base_props((0.5, 0, 0.45, 0), (0.95, 0, 0.95, 0),
                                                     (0.5, 0.5)),
                                       "BackgroundColor3": C3(col), "BackgroundTransparency": 0.55,
                                       "Image": ""})
    glow.add(corner(200))
    glow.add(Inst("UIGradient", "Fade", {"Transparency": NS((0, 0), (0.6, 0.5), (1, 1))}))
    c.add(glow)
    # unknown look (lucky block "?")
    unk = frame("Unknown", (0.5, 0, 0.42, 0), (0, 96, 0, 96), preset="yellow", rad=8, st=4,
                anchor=(0.5, 0.5))
    unk.add(label("Q", "?", (0, 0, 0, 0), (1, 0, 1, 0), 72, st=4, st_color="#9a5c00"))
    c.add(unk)
    known = frame("Known", (0, 0, 0, 0), (1, 0, 1, 0), st=0, rad=0, visible=False)
    known.add(emoji("Icon", p["icon"], (0.5, 0, 0.4, 0), (0, 100, 0, 96), 74, anchor=(0.5, 0.5)))
    known.add(label("Odds", f"1/{p['odds']:,}", (0, 0, 0, 4), (1, -8, 0, 28), 22,
                    color=col if p["tier"] != "Secret" else "#ffffff", align="Right"))
    known.add(label("Count", "x0", (0, 8, 0, 4), (0, 60, 0, 28), 22, align="Left"))
    c.add(known)
    c.add(label("Name", p["name"], (0, 4, 1, -44), (1, -8, 0, 38), 28))
    return c


def index_window():
    w, h = 960, 700
    root, body = window("IndexWindow", "Index", "📘", "blue", w, h)
    root.props["Position"] = U2(0.5, -140, 0.5, 10)
    root.add(label("Counter", "0/16 Found", (1, -110, 0, 50), (0, 260, 0, 40), 32,
                   anchor=(1, 0.5), z=3))
    sc = Inst("ScrollingFrame", "Grid", {
        **base_props((0, 18, 0, 30), (1, -36, 1, -48)), "BackgroundTransparency": 1,
        "ScrollBarThickness": 10, "CanvasSize": U2(0, 0, 0, 0),
        "AutomaticCanvasSize": "Y", "ScrollBarImageColor3": C3("#ffffff")})
    sc.add(Inst("UIGridLayout", "Layout", {"CellSize": U2(0, 206, 0, 206),
                                           "CellPadding": U2(0, 14, 0, 14),
                                           "SortOrder": "LayoutOrder"}))
    sc.add(Inst("UIPadding", "Pad", {"PaddingTop": UD(0, 6), "PaddingLeft": UD(0, 6)}))
    for p in piece_list():
        sc.add(piece_card(p, 206))
    body.add(sc)
    tabs = frame("Tabs", (1, 24, 0, 40), (0, 250, 0, 520), st=0, rad=0)
    presets = {"Common": "gray", "Rare": "blue", "Epic": "purple", "Legendary": "orange",
               "Mythical": "red", "Secret": "dark"}
    tabs.add(button("Tab_All", "All", (0, 0, 0, 0), (1, 0, 0, 70), "green", 40))
    for i, t in enumerate(TIERS):
        tabs.add(button(f"Tab_{t['id']}", t["id"], (0, 0, 0, 84 + i * 84), (1, 0, 0, 70),
                        presets[t["id"]], 40))
    root.add(tabs)
    return root


def reward_cell(name, rw, preset, pos, size):
    c = frame(name, pos, size, preset=preset, rad=10, st=4)
    c.add(label("Name", rw["label"], (0, 2, 0, 2), (1, -4, 0, 34), 24, scaled=False))
    c.add(emoji("Icon", rw["icon"], (0.5, 0, 0.55, 0), (0, 80, 0, 76), 60, anchor=(0.5, 0.5)))
    c.add(label("Check", "✔", (1, -4, 1, -2), (0, 44, 0, 44), 40, color="#5fff3a",
                anchor=(1, 1), visible=False))
    c.add(label("Lock", "🔒", (1, -4, 1, -2), (0, 44, 0, 44), 34, anchor=(1, 1), st=0,
                visible=False))
    c.add(frame("Claimable", (0, 0, 0, 0), (1, 0, 1, 0), color="#ffffff", transp=0.75, rad=10,
                st=4, st_color="#7dff4f", visible=False))
    return c


def pass_window():
    w, h = 1180, 680
    root, body = window("PassWindow", "Season Pass", "🎟️", "orange", w, h)
    root.children[1].add(button("PremiumButton", "Premium Pass", (1, -104, 0.5, 0),
                                (0, 290, 0, 70), "yellow", 36, anchor=(1, 0.5)))
    # row labels
    body.add(button("LvlHeader", "Lvl.", (0, 18, 0, 26), (0, 170, 0, 54), "dark", 34))
    fr = frame("FreeLabel", (0, 18, 0, 92), (0, 170, 0, 190), preset="blue", rad=12, st=4)
    fr.add(emoji("Icon", "🎟️", (0.5, 0, 0.42, 0), (0, 110, 0, 100), 80, anchor=(0.5, 0.5)))
    fr.add(label("Text", "FREE", (0, 0, 1, -50), (1, 0, 0, 44), 38))
    body.add(fr)
    pr = frame("PremiumLabel", (0, 18, 0, 294), (0, 170, 0, 190), preset="gold", rad=12, st=4)
    pr.add(emoji("Icon", "🎫", (0.5, 0, 0.42, 0), (0, 110, 0, 100), 80, anchor=(0.5, 0.5)))
    pr.add(label("Text", "PREMIUM", (0, 0, 1, -50), (1, 0, 0, 44), 32))
    body.add(pr)
    col_w = 196
    sc = Inst("ScrollingFrame", "Track", {
        **base_props((0, 200, 0, 20), (1, -218, 0, 476)), "BackgroundTransparency": 1,
        "ScrollBarThickness": 10, "CanvasSize": U2(0, len(PASS) * col_w + 10, 0, 0),
        "ScrollingDirection": "X", "ScrollBarImageColor3": C3("#ffffff")})
    for p in PASS:
        lvl = p["level"]
        x = (lvl - 1) * col_w
        col = frame(f"Level_{lvl}", (0, x, 0, 0), (0, col_w - 14, 1, -14), st=0, rad=0)
        col.add(button("Header", str(lvl), (0, 0, 0, 6), (1, 0, 0, 54), "dark", 34))
        col.add(reward_cell("Free", p["free"], "dark", (0, 0, 0, 72), (1, 0, 0, 190)))
        col.add(reward_cell("Premium", p["premium"], "dark", (0, 0, 0, 274), (1, 0, 0, 190)))
        sc.add(col)
    body.add(sc)
    bt = frame("Bottom", (0, 18, 1, -100), (1, -36, 0, 84), preset="dark", rad=12, st=4)
    bt.add(label("LevelText", "Lvl 1", (0, 16, 0, 0), (0, 150, 1, 0), 50, align="Left"))
    bt.add(bar("Bar", (0, 170, 0.5, 0), (0, 480, 0, 46), 0.0, anchor=(0, 0.5), text="0/100 XP",
               ts=30))
    bt.add(button("SkipButton", "SKIP", (0, 680, 0.5, 0), (0, 200, 0, 64), "purple", 40,
                  anchor=(0, 0.5)))
    bt.add(button("ClaimButton", "CLAIM", (0, 896, 0.5, 0), (0, 200, 0, 64), "green", 40,
                  anchor=(0, 0.5)))
    body.add(bt)
    return root


def rebirth_window():
    w, h = 800, 520
    root, body = window("RebirthWindow", "Rebirth", "🔄", "purple", w, h)
    cur = frame("Current", (0, 24, 0, 34), (0, 300, 0, 110), preset="green", rad=12, st=4)
    cur.add(label("Title", "Rebirth 0", (0, 0, 0, 2), (1, 0, 0, 40), 32))
    cur.add(label("Value", "X1 Money", (0, 0, 0, 40), (1, 0, 0, 64), 52))
    body.add(cur)
    body.add(label("Arrow", "➡", (0.5, 0, 0, 89), (0, 100, 0, 80), 70, anchor=(0.5, 0.5),
                   color="#cfe6ff"))
    nxt = frame("Next", (1, -24, 0, 34), (0, 300, 0, 110), preset="green", rad=12, st=4,
                anchor=(1, 0))
    nxt.add(label("Title", "Rebirth 1", (0, 0, 0, 2), (1, 0, 0, 40), 32))
    nxt.add(label("Value", "X1.3 Money", (0, 0, 0, 40), (1, 0, 0, 64), 52))
    body.add(nxt)
    req = frame("Requirements", (0, 24, 0, 162), (1, -48, 0, 130), preset="dark", rad=12, st=4)
    req.add(label("Title", "Requirements:", (0, 0, 0, 6), (1, 0, 0, 36), 34))
    req.add(label("ReqText", "Have $100K (resets cash and track pieces)", (0, 10, 0, 42),
                  (1, -20, 0, 32), 26, color="#e6ecff"))
    req.add(bar("Bar", (0, 16, 1, -44), (1, -32, 0, 34), 0.0, text="$0 / $100K", ts=24))
    body.add(req)
    body.add(button("RebirthButton", "Rebirth", (0, 24, 1, -26), (0, 290, 0, 100), "green", 54,
                    anchor=(0, 1)))
    body.add(label("Or", "OR", (0.5, 0, 1, -76), (0, 100, 0, 60), 46, anchor=(0.5, 0.5)))
    body.add(button("SkipButton", "Skip", (1, -24, 1, -26), (0, 290, 0, 100), "purple", 50,
                    anchor=(1, 1), sub="[keep your stats]"))
    sk = body.children[-1]
    sk.add(label("Price", robux(PRODUCTS["DevProducts"]["SkipRebirth"]["price"]),
                 (1, 10, 0, -26), (0, 90, 0, 44), 34, color="#7dff6b", anchor=(1, 0)))
    return root


BRANCH_PRESET = {"Money": "green", "Luck": "cyan", "Speed": "orange", "Spin": "purple",
                 "Track": "blue"}


def upgrades_window():
    w, h = 1240, 760
    root, body = window("UpgradesWindow", "Upgrades", "⬆️", "green", w, h)
    tree = frame("Tree", (0, 18, 0, 22), (1, -36, 0, 500), color="#1c2340", transp=0.2, rad=12,
                 st=3)
    gx, gy = 230, 96
    ox, oy = 90, 58
    node_r = 76

    def pos(u):
        return ox + u["col"] * gx, oy + u["row"] * gy

    byid = {u["id"]: u for u in UPGRADES}
    # lines first (behind nodes)
    for u in UPGRADES:
        if not u["requires"]:
            continue
        a = pos(byid[u["requires"]])
        b = pos(u)
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        ln = frame(f"Line_{u['id']}", (0, (a[0] + b[0]) / 2, 0, (a[1] + b[1]) / 2),
                   (0, L, 0, 10), color="#4a5578", rad=4, st=0, anchor=(0.5, 0.5))
        ln.props["Rotation"] = math.degrees(math.atan2(dy, dx))
        tree.add(ln)
    for u in UPGRADES:
        x, y = pos(u)
        n = button(f"Node_{u['id']}", "", (0, x, 0, y), (0, node_r, 0, node_r),
                   BRANCH_PRESET[u["branch"]], 1, anchor=(0.5, 0.5), rad=node_r // 2, st=5)
        n.children = [c for c in n.children if c.name != "Label"]
        n.add(emoji("Icon", u["icon"], (0, 0, 0, 0), (1, 0, 1, 0), 40))
        n.add(label("Level", "", (0.5, 0, 1, 2), (0, 160, 0, 26), 20, anchor=(0.5, 0)))
        n.add(frame("Locked", (0, 0, 0, 0), (1, 0, 1, 0), color="#000000", transp=0.5,
                    rad=node_r // 2, st=0))
        n.add(label("Owned", "✔", (1, 6, 0, -6), (0, 34, 0, 34), 30, color="#5fff3a",
                    anchor=(1, 0), visible=False))
        tree.add(n)
    body.add(tree)
    info = frame("Info", (0, 18, 1, -18), (1, -36, 0, 150), preset="dark", rad=12, st=4,
                 anchor=(0, 1))
    info.add(emoji("Icon", "🔧", (0, 16, 0.5, 0), (0, 110, 0, 110), 80, anchor=(0, 0.5)))
    info.add(label("NameText", "Engine Tune", (0, 140, 0, 14), (0, 560, 0, 52), 46,
                   align="Left"))
    info.add(label("DescText", "+10% Money", (0, 140, 0, 70), (0, 560, 0, 40), 32,
                   color="#cfe6ff", align="Left"))
    info.add(label("CostText", "$500", (1, -340, 0.5, 0), (0, 300, 0, 60), 46, color="#7dff4f",
                   align="Right", anchor=(1, 0.5)))
    info.add(button("BuyButton", "BUY", (1, -18, 0.5, 0), (0, 300, 0, 96), "green", 54,
                    anchor=(1, 0.5)))
    body.add(info)
    return root


def car_window():
    w, h = 1210, 740
    root, body = window("CarShopWindow", "Car Dealer", "🚗", "blue", w, h)
    sc = Inst("ScrollingFrame", "Grid", {
        **base_props((0, 18, 0, 28), (1, -36, 1, -46)), "BackgroundTransparency": 1,
        "ScrollBarThickness": 10, "CanvasSize": U2(0, 0, 0, 0), "AutomaticCanvasSize": "Y"})
    sc.add(Inst("UIGridLayout", "Layout", {"CellSize": U2(0, 218, 0, 296),
                                           "CellPadding": U2(0, 12, 0, 14),
                                           "SortOrder": "LayoutOrder"}))
    sc.add(Inst("UIPadding", "Pad", {"PaddingTop": UD(0, 6), "PaddingLeft": UD(0, 6)}))
    for c in car_list():
        card = frame(f"Car_{c['id']}", (0, 0, 0, 0), (0, 218, 0, 296), preset="dark", rad=12,
                     st=4)
        card.props["LayoutOrder"] = c["order"]
        vp = Inst("ViewportFrame", "Viewport", {
            **base_props((0.5, 0, 0, 8), (1, -16, 0, 136), (0.5, 0)),
            "BackgroundColor3": C3("#9fd8ff"), "BackgroundTransparency": 0.6,
            "Ambient": C3("#c8c8c8"), "LightColor": C3("#ffffff")})
        vp.add(corner(10))
        card.add(vp)
        card.add(label("NameText", c["name"], (0, 4, 0, 146), (1, -8, 0, 38), 30, scaled=False))
        card.add(label("StatsText", f"⚡{c['speed']}  💵x{c['mult']:g}", (0, 4, 0, 184),
                       (1, -8, 0, 30), 24, color="#cfe6ff"))
        price = "FREE" if c["price"] == 0 else short(c["price"])
        card.add(button("PriceButton", price, (0.5, 0, 1, -10), (1, -22, 0, 66), "green", 32,
                        anchor=(0.5, 1)))
        sc.add(card)
    body.add(sc)
    return root


def style_window():
    w, h = 1120, 660
    root, body = window("StyleShopWindow", "Island Styles", "🎨", "pink", w, h)
    for i, s in enumerate(style_list()):
        x = 22 + (i % 4) * 268
        y = 30 + (i // 4) * 272
        card = frame(f"Style_{s['id']}", (0, x, 0, y), (0, 254, 0, 258), preset="dark", rad=12,
                     st=4)
        sw = frame("Swatch", (0.5, 0, 0, 10), (1, -20, 0, 104), color=s["grass"], rad=10, st=3,
                   anchor=(0.5, 0), clip=True)
        sw.add(frame("Dirt", (0, 0, 0.55, 0), (1, 0, 0.25, 0), color=s["dirt"], rad=0, st=0))
        sw.add(frame("Rock", (0, 0, 0.8, 0), (1, 0, 0.2, 0), color=s["rock"], rad=0, st=0))
        card.add(sw)
        card.add(label("NameText", s["name"], (0, 4, 0, 118), (1, -8, 0, 40), 32))
        bonus = "Starter style" if s["bonus"] == 0 else f"+{int(s['bonus'] * 100)}% Money"
        card.add(label("BonusText", bonus, (0, 4, 0, 156), (1, -8, 0, 30), 26,
                       color="#9dff7a"))
        price = "FREE" if s["price"] == 0 else short(s["price"])
        card.add(button("PriceButton", price, (0.5, 0, 1, -10), (1, -22, 0, 62), "green", 32,
                        anchor=(0.5, 1)))
        body.add(card)
    return root


def potion_window():
    w, h = 1020, 470
    root, body = window("PotionShopWindow", "Potions", "🧪", "purple", w, h)
    for i, p in enumerate(POTIONS):
        x = 22 + i * 246
        card = frame(f"Potion_{p['id']}", (0, x, 0, 30), (0, 232, 0, 330), preset="dark",
                     rad=12, st=4)
        circle = frame("Bg", (0.5, 0, 0, 14), (0, 130, 0, 130), color=p["color"], transp=0.4,
                       rad=65, st=4, anchor=(0.5, 0))
        circle.add(emoji("Icon", "🧪", (0, 0, 0, 0), (1, 0, 1, 0), 84))
        card.add(circle)
        card.add(label("NameText", p["name"], (0, 4, 0, 150), (1, -8, 0, 40), 32))
        card.add(label("DescText", f"{p['desc']} for {p['duration'] // 60} min", (0, 6, 0, 190),
                       (1, -12, 0, 52), 24, color="#cfe6ff", wrap=True))
        card.add(label("TimerText", "", (0, 4, 0, 238), (1, -8, 0, 26), 22, color="#ffe14d"))
        card.add(button("BuyButton", f"${p['price']:,}", (0.5, 0, 1, -10), (1, -22, 0, 62),
                        "green", 32, anchor=(0.5, 1)))
        body.add(card)
    return root


def lucky_window():
    w, h = 1020, 470
    root, body = window("LuckyShopWindow", "Lucky Blocks", "🎲", "yellow", w, h)
    for i, b in enumerate(LUCKY_BLOCKS):
        x = 22 + i * 246
        card = frame(f"Lucky_{b['id']}", (0, x, 0, 30), (0, 232, 0, 330), preset="dark", rad=12,
                     st=4)
        blk = frame("Block", (0.5, 0, 0, 18), (0, 120, 0, 120), color=b["color"], rad=10, st=5,
                    anchor=(0.5, 0))
        blk.add(label("Q", "?", (0, 0, 0, 0), (1, 0, 1, 0), 92, st=5))
        card.add(blk)
        card.add(label("NameText", b["name"], (0, 4, 0, 150), (1, -8, 0, 40), 26))
        card.add(label("LuckText", f"🍀 x{b['luck']} Luck Spin", (0, 4, 0, 192), (1, -8, 0, 34),
                       26, color="#9dff7a"))
        card.add(label("OwnedText", "Owned: 0", (0, 4, 0, 230), (1, -8, 0, 30), 24,
                       color="#cfe6ff"))
        card.add(button("BuyButton", short(b["price"]), (0, 11, 1, -10), (0.5, -16, 0, 62),
                        "green", 28, anchor=(0, 1)))
        card.add(button("OpenButton", "OPEN", (1, -11, 1, -10), (0.5, -16, 0, 62), "yellow", 28,
                        anchor=(1, 1)))
        body.add(card)
    return root


def spin_popup():
    p = frame("SpinPopup", (0.5, 0, 0, 150), (0, 700, 0, 250), preset="dark", rad=18, st=6,
              anchor=(0.5, 0), visible=False)
    p.add(label("Header", "YOU ROLLED", (0, 0, 0, 8), (1, 0, 0, 50), 44, color="#ffe14d"))
    p.add(emoji("Icon", "⬆️", (0, 24, 0.5, 18), (0, 110, 0, 110), 84, anchor=(0, 0.5)))
    p.add(label("PieceName", "Straight", (0, 150, 0, 62), (1, -170, 0, 76), 66, align="Left",
                st=5))
    p.add(label("Tier", "Common", (0, 150, 0, 136), (0, 260, 0, 40), 36, align="Left"))
    p.add(label("Odds", "1 in 2", (1, -24, 0, 136), (0, 280, 0, 40), 34, align="Right",
                anchor=(1, 0)))
    p.add(label("Status", "Added to your track!", (0, 0, 1, -50), (1, 0, 0, 40), 32,
                color="#9dff7a"))
    return p


def toasts():
    holder = frame("Toasts", (0.5, 0, 0, 130), (0, 700, 0, 400), anchor=(0.5, 0), st=0, rad=0)
    holder.add(Inst("UIListLayout", "Layout", {"Padding": UD(0, 8), "SortOrder": "LayoutOrder",
                                               "HorizontalAlignment": "Center"}))
    return holder


def templates():
    t = Inst("Folder", "Templates")
    toast = frame("Toast", (0, 0, 0, 0), (0, 640, 0, 64), preset="dark", rad=14, st=4)
    toast.add(label("Text", "Message", (0, 10, 0, 0), (1, -20, 1, 0), 34))
    t.add(toast)
    pot = frame("PotionTimer", (0, 0, 0, 0), (0, 92, 0, 110), preset="purple", rad=12, st=4)
    pot.add(emoji("Icon", "🧪", (0.5, 0, 0, 2), (0, 70, 0, 60), 50, anchor=(0.5, 0)))
    pot.add(label("Time", "5:00", (0, 0, 1, -40), (1, 0, 0, 36), 28))
    t.add(pot)
    return t


def build():
    gui = Inst("ScreenGui", "MainGui", {"ResetOnSpawn": False, "IgnoreGuiInset": True,
                                       "ZIndexBehavior": "Sibling"})
    root = frame("Root", (0.5, 0, 0.5, 0), (0, 1920, 0, 1080), anchor=(0.5, 0.5), st=0, rad=0)
    root.add(Inst("UIScale", "Scale", {"Scale": 1}))
    root.add(hud())
    wins = frame("Windows", (0, 0, 0, 0), (1, 0, 1, 0), st=0, rad=0)
    for f in (shop_window, daily_window, index_window, pass_window, rebirth_window,
              upgrades_window, car_window, style_window, potion_window, lucky_window):
        wins.add(f())
    root.add(wins)
    root.add(spin_popup())
    root.add(toasts())
    gui.add(root)
    gui.add(templates())
    return gui


if __name__ == "__main__":
    write_model(build(), "StarterGui/MainGui.model.json")

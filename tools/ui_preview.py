"""Approximate HTML renderer for the generated Roblox UI (for screenshots without Studio).

Usage: python ui_preview.py <WindowName|HUD> [...]   -> renders/ui_<name>.png
"""
import base64
import html
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI = os.path.join(ROOT, "src/StarterGui/MainGui.model.json")
W, H = 1920, 1080


def c3(v):
    r, g, b = v["Color3"]
    return int(r * 255), int(g * 255), int(b * 255)


def rgba(v, a=1.0):
    r, g, b = c3(v)
    return f"rgba({r},{g},{b},{a:.3f})"


def udim2(v):
    (xs, xo), (ys, yo) = v["UDim2"]
    return xs, xo, ys, yo


def child(node, cls):
    for c in node.get("Children", []):
        if c["ClassName"] == cls:
            return c
    return None


def props(n):
    return n.get("Properties", {})


def gradient_css(g):
    p = props(g)
    kps = p.get("Color", {}).get("ColorSequence", {}).get("keypoints", [])
    if not kps:
        return None
    rot = p.get("Rotation", 0)
    stops = ", ".join(f"rgb({int(k['color'][0]*255)},{int(k['color'][1]*255)},"
                      f"{int(k['color'][2]*255)}) {k['time']*100:.1f}%" for k in kps)
    return f"linear-gradient({rot + 90}deg, {stops})"


def text_html(n, w, h):
    p = props(n)
    txt = p.get("Text", "")
    if not txt:
        return ""
    txt = txt.replace("", "⏣")
    ts = p.get("TextSize", 14)
    if p.get("TextScaled"):
        ts = min(h * 0.8, w / max(1, len(txt)) * 1.9)
    col = rgba(p.get("TextColor3", {"Color3": [0, 0, 0]}))
    xa = {"Left": "flex-start", "Right": "flex-end"}.get(p.get("TextXAlignment"), "center")
    ya = {"Top": "flex-start", "Bottom": "flex-end"}.get(p.get("TextYAlignment"), "center")
    ta = {"Left": "left", "Right": "right"}.get(p.get("TextXAlignment"), "center")
    st = child(n, "UIStroke")
    stroke = ""
    if st and props(st).get("ApplyStrokeMode") != "Border":
        sp = props(st)
        th = sp.get("Thickness", 1)
        stroke = (f"-webkit-text-stroke:{th * 2}px {rgba(sp.get('Color', {'Color3': [0, 0, 0]}))};"
                  "paint-order:stroke fill;")
    wrap = "white-space:normal;" if p.get("TextWrapped") else "white-space:nowrap;"
    return (f'<div style="position:absolute;inset:0;display:flex;align-items:{ya};'
            f'justify-content:{xa};text-align:{ta};font-size:{ts}px;color:{col};{stroke}{wrap}'
            f'line-height:1;">{html.escape(txt)}</div>')


def render_node(n, pw, ph, force_visible=(), depth=0):
    cls = n["ClassName"]
    if cls in ("UICorner", "UIStroke", "UIGradient", "UIScale", "UIPadding", "UIListLayout",
               "UIGridLayout", "Folder", "ScreenGui"):
        return ""
    p = props(n)
    if p.get("Visible") is False and n["Name"] not in force_visible:
        return ""
    xs, xo, ys, yo = udim2(p.get("Size", {"UDim2": [[0, 0], [0, 0]]}))
    w = pw * xs + xo
    h = ph * ys + yo
    pxs, pxo, pys, pyo = udim2(p.get("Position", {"UDim2": [[0, 0], [0, 0]]}))
    ax, ay = p.get("AnchorPoint", {"Vector2": [0, 0]})["Vector2"]
    x = pw * pxs + pxo - ax * w
    y = ph * pys + pyo - ay * h
    if "_pos" in n:
        x, y = n["_pos"]
    style = [f"position:absolute;left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;"]
    bt = p.get("BackgroundTransparency", 0)
    grad = child(n, "UIGradient")
    gcss = gradient_css(grad) if grad else None
    if bt < 1:
        if gcss:
            style.append(f"background:{gcss};")
            if bt:
                style.append(f"opacity:{1 - bt:.2f};")
        elif "BackgroundColor3" in p:
            style.append(f"background:{rgba(p['BackgroundColor3'], 1 - bt)};")
    cr = child(n, "UICorner")
    if cr:
        s, o = props(cr)["CornerRadius"]["UDim"]
        style.append(f"border-radius:{min(o + s * min(w, h), min(w, h) / 2):.1f}px;")
    st = child(n, "UIStroke")
    if st and props(st).get("ApplyStrokeMode") == "Border":
        sp = props(st)
        style.append(f"box-shadow:0 0 0 {sp.get('Thickness', 1)}px "
                     f"{rgba(sp.get('Color', {'Color3': [0, 0, 0]}))};")
    if p.get("Rotation"):
        style.append(f"transform:rotate({p['Rotation']}deg);")
    if cls == "ScrollingFrame" or p.get("ClipsDescendants"):
        style.append("overflow:hidden;")
    inner = ""
    if cls in ("TextLabel", "TextButton"):
        inner += text_html(n, w, h)
    kids = [c for c in n.get("Children", [])]
    grid = child(n, "UIGridLayout")
    lst = child(n, "UIListLayout")
    pad = child(n, "UIPadding")
    pl = pt = 0
    if pad:
        pl = props(pad).get("PaddingLeft", {"UDim": [0, 0]})["UDim"][1]
        pt = props(pad).get("PaddingTop", {"UDim": [0, 0]})["UDim"][1]
    if grid or lst:
        items = [c for c in kids if c["ClassName"] not in ("UIGridLayout", "UIListLayout",
                                                           "UIPadding", "UICorner", "UIStroke",
                                                           "UIGradient")]
        items.sort(key=lambda c: props(c).get("LayoutOrder", 0))
        if grid:
            gp = props(grid)
            cw, chh = udim2(gp["CellSize"])[1], udim2(gp["CellSize"])[3]
            px, py = udim2(gp["CellPadding"])[1], udim2(gp["CellPadding"])[3]
            cols = max(1, int((w - pl + px) // (cw + px)))
            for i, it in enumerate(items):
                it = dict(it)
                pr = dict(props(it))
                pr["Size"] = {"UDim2": [[0, cw], [0, chh]]}
                it["Properties"] = pr
                it["_pos"] = (pl + (i % cols) * (cw + px), pt + (i // cols) * (chh + py))
                inner += render_node(it, w, h, force_visible, depth + 1)
        else:
            lp = props(lst)
            gap = lp.get("Padding", {"UDim": [0, 0]})["UDim"][1]
            horiz = lp.get("FillDirection") == "Horizontal"
            off = 0
            for it in items:
                it = dict(it)
                sx, so, sy, syo = udim2(props(it)["Size"])
                iw, ih = w * sx + so, h * sy + syo
                if props(it).get("AutomaticSize") == "X":
                    iw = len(props(it).get("Text", "")) * props(it).get("TextSize", 14) * 0.58
                    pr = dict(props(it))
                    pr["Size"] = {"UDim2": [[0, iw], [sy, syo]]}
                    it["Properties"] = pr
                if lp.get("VerticalAlignment") == "Center" and horiz:
                    it["_pos"] = (off, (h - ih) / 2)
                if "_pos" not in it:
                    it["_pos"] = (off, 0) if horiz else ((w - iw) / 2 if lp.get(
                        "HorizontalAlignment") == "Center" else 0, off)
                inner += render_node(it, w, h, force_visible, depth + 1)
                off += (iw if horiz else ih) + gap
    else:
        for c in kids:
            inner += render_node(c, w, h, force_visible, depth + 1)
    return f'<div data-n="{html.escape(n["Name"])}" style="{"".join(style)}">{inner}</div>'


def build_html(show, bg):
    gui = json.load(open(GUI, encoding="utf-8"))
    root = [c for c in gui["Children"] if c["Name"] == "Root"][0]
    font = base64.b64encode(open(os.path.join(ROOT, "ui/fonts/Fredoka-Bold.ttf"), "rb").read())
    bgdata = base64.b64encode(open(bg, "rb").read()).decode() if bg else ""
    body = render_node(root, W, H, force_visible=show)
    dim = ('<div style="position:absolute;inset:0;background:rgba(0,0,0,0.25)"></div>'
           if any(s.endswith("Window") for s in show) else "")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:Fred;src:url(data:font/ttf;base64,{font.decode()});}}
body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;font-family:Fred,'Noto Color Emoji';
background:url(data:image/png;base64,{bgdata}) center/cover;}}
</style></head><body>{dim}{body}</body></html>"""


if __name__ == "__main__":
    names = sys.argv[1:] or ["HUD"]
    bg = os.path.join(ROOT, "renders/preview_plot.png")
    jobs = []
    for nm in names:
        show = [] if nm == "HUD" else [nm]
        out_html = os.path.join(ROOT, f"renders/ui_{nm}.html")
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(build_html(show, bg))
        jobs.append((out_html, os.path.join(ROOT, f"renders/ui_{nm}.png")))
    js = "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();" \
         "const p=await b.newPage({viewport:{width:%d,height:%d}});" % (W, H)
    for h_, png in jobs:
        js += f"await p.goto('file://{h_}');await p.waitForTimeout(300);" \
              f"await p.screenshot({{path:'{png}'}});"
    js += "await b.close();})();"
    env = dict(os.environ, NODE_PATH=subprocess.check_output(["npm", "root", "-g"]).decode().strip())
    subprocess.run(["node", "-e", js], check=True, env=env)
    for h_, png in jobs:
        os.remove(h_)
        print("wrote", png)

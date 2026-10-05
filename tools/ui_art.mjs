// Chunky game-style button art (SVG -> transparent PNG) for the HUD.
// Writes assets/ui/svg/<name>.svg (importable into Figma) and assets/ui/<name>.png (512 px).
// Run: node tools/ui_art.mjs   (needs the preinstalled Playwright Chromium)
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)(process.env.PW || "playwright");
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const OUT = path.join(ROOT, "assets", "ui");
fs.mkdirSync(path.join(OUT, "svg"), { recursive: true });
const FONT = fs.readFileSync(path.join(ROOT, "ui/fonts/LilitaOne.ttf")).toString("base64");

const INK = "#1b1530";

// ---------------------------------------------------------------- icons (white, 0..100 box)
const ICONS = {
  music: `<path d="M38 18 L82 10 L82 64 A12 10 0 1 1 72 54 L72 26 L48 30 L48 72 A12 10 0 1 1 38 62 Z"/>`,
  sound: `<path d="M14 38 L30 38 L50 20 L50 80 L30 62 L14 62 Z"/>
          <path d="M62 34 Q72 50 62 66" fill="none" stroke-width="8" stroke-linecap="round"/>
          <path d="M72 24 Q88 50 72 76" fill="none" stroke-width="8" stroke-linecap="round"/>`,
  sparkle: `<path d="M44 8 Q50 40 82 46 Q50 52 44 88 Q38 52 6 46 Q38 40 44 8 Z"/>
            <path d="M78 6 Q81 18 92 20 Q81 23 78 34 Q75 23 64 20 Q75 18 78 6 Z"/>
            <path d="M80 66 Q82 74 90 76 Q82 78 80 86 Q78 78 70 76 Q78 74 80 66 Z"/>`,
  auto: `<g transform="scale(4.1667)"><path style="stroke-width:1.5px" d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/></g>`,
  eye: `<path d="M6 50 Q50 6 94 50 Q50 94 6 50 Z"/>
        <circle cx="50" cy="50" r="17" fill="#2a2140"/><circle cx="56" cy="44" r="6" fill="#fff"/>`,
  eyeoff: `<path d="M6 50 Q50 6 94 50 Q50 94 6 50 Z"/>
           <circle cx="50" cy="50" r="17" fill="#2a2140"/>
           <path d="M14 86 L86 14" fill="none" stroke-width="12" stroke-linecap="round"/>`,
};

// ---------------------------------------------------------------- button builder
function button({ name, top, bottom, icon, label, off = false, glow = null, w = 256, h = 256 }) {
  const id = name.replace(/[^a-z0-9]/gi, "");
  const face = off ? ["#c3c8d4", "#7b8196"] : [top, bottom];
  const depth = off ? "#4d5266" : shade(bottom, -0.38);
  const r = Math.round(Math.min(w, h) * 0.24);
  const fw = w - 24, fh = h - 34;
  const iconSize = label ? fh * 0.5 : fh * 0.62;
  const iconY = label ? 14 + fh * 0.1 : 12 + (fh - iconSize) / 2;
  const iconX = (w - iconSize) / 2;
  const labelSvg = label ? `
    <text x="${w / 2}" y="${12 + fh * 0.86}" text-anchor="middle" font-family="Lilita" font-size="${fh * 0.21}"
      fill="#fff" stroke="${INK}" stroke-width="${fh * 0.05}" stroke-linejoin="round" paint-order="stroke"
      letter-spacing="1">${label}</text>` : "";
  const offSlash = off ? `<path d="M${w * 0.2} ${h * 0.78} L${w * 0.8} ${h * 0.18}" stroke="${INK}" stroke-width="30" stroke-linecap="round"/>
    <path d="M${w * 0.2} ${h * 0.78} L${w * 0.8} ${h * 0.18}" stroke="#ff3d5a" stroke-width="17" stroke-linecap="round"/>` : "";
  const glowSvg = glow ? `<rect x="2" y="2" width="${w - 4}" height="${h - 4}" rx="${r + 8}" fill="none"
      stroke="${glow}" stroke-width="8" opacity="0.9" filter="url(#blur${id})"/>` : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <defs>
    <style>@font-face{font-family:Lilita;src:url(data:font/ttf;base64,${FONT})}</style>
    <linearGradient id="face${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${face[0]}"/><stop offset="1" stop-color="${face[1]}"/></linearGradient>
    <linearGradient id="shine${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0.05"/></linearGradient>
    <filter id="blur${id}" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
    <filter id="drop${id}" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="0" flood-color="${INK}" flood-opacity="0.55"/></filter>
  </defs>
  ${glowSvg}
  <!-- depth (3D bottom edge) -->
  <rect x="12" y="22" width="${fw}" height="${fh}" rx="${r}" fill="${depth}" stroke="${INK}" stroke-width="8"/>
  <!-- face -->
  <rect x="12" y="12" width="${fw}" height="${fh}" rx="${r}" fill="url(#face${id})" stroke="${INK}" stroke-width="8"/>
  <!-- inner rim + gloss -->
  <rect x="22" y="22" width="${fw - 20}" height="${fh - 20}" rx="${r - 8}" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="4"/>
  <path d="M${12 + r} 22 H${12 + fw - r} Q${12 + fw - 12} 22 ${12 + fw - 14} ${22 + fh * 0.36}
           Q${w / 2} ${22 + fh * 0.48} 26 ${22 + fh * 0.36} Q24 22 ${12 + r} 22 Z" fill="url(#shine${id})"/>
  <!-- icon -->
  <g filter="url(#drop${id})">
    <svg x="${iconX}" y="${iconY}" width="${iconSize}" height="${iconSize}" viewBox="0 0 100 100">
      <g fill="#fff" stroke="${INK}" stroke-width="6" stroke-linejoin="round" paint-order="stroke">${ICONS[icon]
        .replace(/stroke-width="(\d+)"/g, (m, v) => `stroke-width="${v}" stroke="#fff"`)}</g>
    </svg>
  </g>
  ${labelSvg}
  ${offSlash}
</svg>`;
}

function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16);
  const c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.max(0, Math.min(255, Math.round(v * (1 + k)))));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
}

const ART = [
  { name: "music_on", top: "#ff8be6", bottom: "#a637ff", icon: "music" },
  { name: "music_off", top: "#ff8be6", bottom: "#a637ff", icon: "music", off: true },
  { name: "sfx_on", top: "#7ef0ff", bottom: "#2a7bff", icon: "sound" },
  { name: "sfx_off", top: "#7ef0ff", bottom: "#2a7bff", icon: "sound", off: true },
  { name: "vfx_on", top: "#fff07a", bottom: "#ff8a1a", icon: "sparkle" },
  { name: "vfx_off", top: "#fff07a", bottom: "#ff8a1a", icon: "sparkle", off: true },
  { name: "auto_off", top: "#8fd7ff", bottom: "#3a62d9", icon: "auto", label: "AUTO" },
  { name: "auto_on", top: "#b8ff6a", bottom: "#16b83a", icon: "auto", label: "AUTO ON", glow: "#b8ff6a" },
  { name: "hide", top: "#d8a8ff", bottom: "#7a3be0", icon: "eyeoff", label: "HIDE" },
  { name: "show", top: "#ffd27a", bottom: "#ff7a2a", icon: "eye", label: "SHOW" },
];

// plain white icons with a dark outline (used on native game buttons)
function iconOnly(icon, size = 256) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="-8 -8 116 116">
  <g fill="#fff" stroke="${INK}" stroke-width="9" stroke-linejoin="round" paint-order="stroke">${ICONS[icon]
    .replace(/stroke-width="(\d+(?:\.\d+)?)"/g, (m, v) => `stroke-width="${v}" stroke="#fff"`)}</g></svg>`;
}
const ICON_ONLY = [["icon_auto", "auto"], ["icon_eye", "eye"], ["icon_eyeoff", "eyeoff"]];

const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" }).catch(
  () => chromium.launch());
const page = await browser.newPage({ deviceScaleFactor: 2 });
const sheet = [];
for (const a of ART) {
  const svg = button(a);
  fs.writeFileSync(path.join(OUT, "svg", a.name + ".svg"), svg);
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
  await page.evaluate(() => document.fonts.ready);
  const el = await page.$("svg");
  await el.screenshot({ path: path.join(OUT, a.name + ".png"), omitBackground: true });
  sheet.push(svg);
  console.log("wrote", a.name);
}
for (const [name, icon] of ICON_ONLY) {
  const svg = iconOnly(icon);
  fs.writeFileSync(path.join(OUT, "svg", name + ".svg"), svg);
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
  const el = await page.$("svg");
  await el.screenshot({ path: path.join(OUT, name + ".png"), omitBackground: true });
  console.log("wrote", name);
}
// contact sheet on a game-like background for review
await page.setViewportSize({ width: 1400, height: 330 });
await page.setContent(`<html><body style="margin:0;background:linear-gradient(#7fd3ff,#4fb24a);display:flex;
  flex-wrap:wrap;gap:6px;padding:10px">${sheet.map((s) => `<div style="width:128px;height:128px">${s.replace(/width="256" height="256"/, 'width="128" height="128"')}</div>`).join("")}</body></html>`);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: path.join(ROOT, "renders", "ui_buttons_sheet.png") });
await browser.close();

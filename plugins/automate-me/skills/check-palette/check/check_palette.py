"""Fail a rendered page whose large backgrounds are beige, or far from a locked palette.

Usage: python3 check_palette.py <url or .html file> [--allow-beige] [--brief FILE]
                                [--palette palette.json] [--max-delta 5] [--min-area 10000]
Exit 0 OK, 1 FAIL, 2 cannot run (missing page, bad input, Playwright or Chromium missing, crash).
"""
import argparse
import colorsys
import json
import math
import pathlib
import re
import sys

CHECK_BEIGE = True
BEIGE_HUE = (25, 60)        # degrees
BEIGE_MIN_SAT = 10          # percent; below this it reads as gray
BEIGE_LIGHT = (88, 98)      # percent; below is a chosen tan, above is white
MAX_DELTA_DEFAULT = 5       # CIEDE2000
MIN_AREA_DEFAULT = 10000    # px2
ELEMENTS = "*"              # CSS selector of the candidate elements
VIEWPORT = {"width": 1280, "height": 800}
ALLOW_LINE = re.compile(r"^\s*(?:[-*]\s*)?allow beige:[ \t]*yes\b", re.I | re.M)
INSTALL = "SKIP: Playwright or Chromium missing. Install: pip install playwright && python3 -m playwright install chromium"

# Returns [selector, [r, g, b]] per checked element, first the page canvas: the html background,
# else the body background, else white. Each painted layer is mixed over its ancestors, scaled by
# the opacity of its element and ancestors; display: contents and invisible ancestors paint nothing.
JS = """([sel, minArea]) => {
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const alpha = c => { ctx.fillStyle = '#000'; ctx.fillStyle = c; ctx.clearRect(0, 0, 1, 1); ctx.fillRect(0, 0, 1, 1);
                       return ctx.getImageData(0, 0, 1, 1).data[3]; };
  const part = e => { let s = e.localName + (e.id ? '#' + e.id : '') + [...e.classList].slice(0, 2).map(c => '.' + c).join('');
    const same = e.parentElement ? [...e.parentElement.children].filter(x => x.localName === e.localName) : [e];
    return same.length > 1 ? s + ':nth-of-type(' + (same.indexOf(e) + 1) + ')' : s; };
  const path = e => { const out = []; for (let x = e; x && out.length < 4; x = x.parentElement) out.unshift(part(x)); return out.join('>'); };
  const op = e => { let o = 1; for (let x = e; x; x = x.parentElement) o *= getComputedStyle(x).opacity; return o; };
  const painted = s => s.display !== 'contents' && s.visibility === 'visible';
  const effective = e => { const layers = [];
    for (let x = e; x; x = x.parentElement) { const s = getComputedStyle(x), a = painted(s) ? alpha(s.backgroundColor) : 0, o = op(x);
      if (a > 0) layers.unshift([s.backgroundColor, o]); if (a === 255 && o === 1) break; }
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 1, 1);
    for (const [c, o] of layers) { ctx.globalAlpha = o; ctx.fillStyle = c; ctx.fillRect(0, 0, 1, 1); }
    ctx.globalAlpha = 1; return [...ctx.getImageData(0, 0, 1, 1).data.slice(0, 3)]; };
  const html = document.documentElement, body = document.body, bg = e => e ? alpha(getComputedStyle(e).backgroundColor) : 0;
  const canvas = bg(html) ? html : bg(body) ? body : html;
  const out = [[path(html), effective(canvas)]];
  for (const e of document.querySelectorAll(sel)) {
    if (e === html || e === canvas) continue;
    const st = getComputedStyle(e), r = e.getBoundingClientRect();
    if (!alpha(st.backgroundColor) || st.visibility !== 'visible' || !r.width || !r.height || r.width * r.height < minArea) continue;
    if (op(e) > 0) out.push([path(e), effective(e)]);
  }
  return out; }"""


def hexstr(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def parse_hex(s):
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", s.strip())
    if not m:
        raise ValueError(f"not a #RRGGBB color: {s}")
    return [int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)]


def hsl(rgb):
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return round(h * 360, 4), round(s * 100, 4), round(l * 100, 4)


def is_beige(rgb):
    h, s, l = hsl(rgb)
    return CHECK_BEIGE and BEIGE_HUE[0] <= h <= BEIGE_HUE[1] and s >= BEIGE_MIN_SAT and BEIGE_LIGHT[0] <= l <= BEIGE_LIGHT[1]


def lab(rgb):
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in rgb]
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883
    f = [t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def delta_e(lab1, lab2):
    """CIEDE2000 (Sharma, Wu and Dalal 2005), kL = kC = kH = 1."""
    (L1, a1, b1), (L2, a2, b2) = lab1, lab2
    cbar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(cbar ** 7 / (cbar ** 7 + 25 ** 7)))
    a1, a2 = a1 * (1 + g), a2 * (1 + g)
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1 = math.degrees(math.atan2(b1, a1)) % 360 if c1 else 0
    h2 = math.degrees(math.atan2(b2, a2)) % 360 if c2 else 0
    dh = 0 if c1 * c2 == 0 else (h2 - h1 if abs(h2 - h1) <= 180 else h2 - h1 - 360 if h2 > h1 else h2 - h1 + 360)
    dH = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(dh / 2))
    lbar, cbar = (L1 + L2) / 2, (c1 + c2) / 2
    hbar = h1 + h2 if c1 * c2 == 0 else (h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    t = (1 - 0.17 * math.cos(math.radians(hbar - 30)) + 0.24 * math.cos(math.radians(2 * hbar))
         + 0.32 * math.cos(math.radians(3 * hbar + 6)) - 0.20 * math.cos(math.radians(4 * hbar - 63)))
    sl = 1 + 0.015 * (lbar - 50) ** 2 / math.sqrt(20 + (lbar - 50) ** 2)
    sc, sh = 1 + 0.045 * cbar, 1 + 0.015 * cbar * t
    rt = -2 * math.sqrt(cbar ** 7 / (cbar ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-(((hbar - 275) / 25) ** 2))))
    return math.sqrt(((L2 - L1) / sl) ** 2 + ((c2 - c1) / sc) ** 2 + (dH / sh) ** 2 + rt * (c2 - c1) / sc * dH / sh)


def load_palette(path):
    data = json.load(open(path))
    values = data.values() if isinstance(data, dict) else data
    if not values:
        raise ValueError(f"palette is empty: {path}")
    return [parse_hex(v) for v in values]


def failures(rows, allow, palette, max_delta):
    out = []
    for sel, rgb in rows:
        if is_beige(rgb) and not allow:
            h, s, l = hsl(rgb)
            out.append(f"FAIL {sel} {hexstr(rgb)} beige (H={h:.0f} S={s:.0f}% L={l:.0f}%)")
        if palette:
            d, near = min((delta_e(lab(rgb), lab(p)), p) for p in palette)
            if d > max_delta:
                out.append(f"FAIL {sel} {hexstr(rgb)} off-palette (nearest {hexstr(near)}, deltaE={d:.1f})")
    return out


def render(target, min_area):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(INSTALL)
        sys.exit(2)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            print(INSTALL)
            sys.exit(2)
        page = browser.new_page(viewport=VIEWPORT)
        resp = page.goto(target, wait_until="load")
        if resp is not None and not resp.ok:
            raise RuntimeError(f"page returned HTTP {resp.status}")
        rows = page.evaluate(JS, [ELEMENTS, min_area])
        browser.close()
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target")
    ap.add_argument("--allow-beige", action="store_true")
    ap.add_argument("--brief")
    ap.add_argument("--palette")
    ap.add_argument("--max-delta", type=float, default=MAX_DELTA_DEFAULT)
    ap.add_argument("--min-area", type=float, default=MIN_AREA_DEFAULT)
    args = ap.parse_args()
    try:
        for name, v in [("--max-delta", args.max_delta), ("--min-area", args.min_area)]:
            if not math.isfinite(v) or v < 0:
                raise ValueError(f"{name} must be a finite number >= 0, got {v}")
        allow = args.allow_beige or bool(args.brief and ALLOW_LINE.search(open(args.brief).read()))
        palette = load_palette(args.palette) if args.palette else None
        target = args.target
        if not re.match(r"^[a-z]+://", target):
            if not pathlib.Path(target).is_file():
                raise FileNotFoundError(f"no such page: {target}")
            target = pathlib.Path(target).resolve().as_uri()
        fails = failures(render(target, args.min_area), allow, palette, args.max_delta)
    except Exception as e:
        print(f"CHECK-PALETTE: ERROR {type(e).__name__}: {e}")
        sys.exit(2)
    for f in fails:
        print(f)
    print(f"CHECK-PALETTE: FAIL ({len(fails)})" if fails else "CHECK-PALETTE: OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

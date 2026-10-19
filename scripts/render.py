#!/usr/bin/env python3
"""Renderiza las slides de un post VALCOM a PNG 1080x1350 (y PDF si es documento de LinkedIn).

Uso:  python3 scripts/render.py posts/2026/10/2026-10-21_slug
Requiere: pip install playwright pillow && python3 -m playwright install chromium

Marcado en textos: *texto* en headline -> dorado; **texto** en body -> dorado.
"""
import html, json, re, sys, pathlib, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
W, H = 1080, 1350


def esc(s):
    return html.escape(s or "")


def rich(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s.replace("\n", "<br>")


DIAG = """<svg class="diag{cls}" viewBox="0 0 540 400" preserveAspectRatio="xMaxYMin slice" aria-hidden="true">
<rect class="f-gold" x="162" y="0" width="189" height="200"/><rect class="f-tint" x="351" y="0" width="189" height="140"/>
<rect class="f-blue" x="162" y="200" width="189" height="200"/><rect class="f-blue2" x="351" y="140" width="189" height="260"/>
<polygon class="f-ground" points="184,400 248,400 551,-24 487,-24"/><polygon class="f-ground" points="389,400 427,400 551,248 551,188"/></svg>"""

CHECK = '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#C9B497" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l4 4 10-10"/></svg>'


def foot(i, n, kind):
    logo = f'<img class="logo" src="{BRAND}/logos/valcom-logo-horizontal.png" alt="">'
    iso = f'<img class="iso" src="{BRAND}/logos/valcom-isotipo.png" alt="">'
    if kind == "cover":
        right = '<div class="swipe">Desliza →</div>' if n > 1 else '<div class="meta">Pregúntale a Valox · IA en ciberseguridad 24/7</div>'
        return f'<div class="foot">{logo}{right}</div>'
    if kind == "closing":
        return f'<div class="foot">{logo}<div class="web">www.valcomsa.com</div></div>'
    return f'<div class="foot">{iso}<div class="page">{i:02d} / {n:02d}</div></div>'


def slide_html(s, i, n):
    lay = s.get("layout", "cover")
    if lay == "cover":
        inner = DIAG.format(cls="") + f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <h1 class="headline">{rich(s.get("headline"))}</h1>
  {f'<p class="body">{rich(s.get("body"))}</p>' if s.get("body") else ''}
</div>'''
    elif lay == "point":
        inner = DIAG.format(cls=" small") + f'''<div class="copy">
  <div class="num">{esc(s.get("number") or f"{i-1:02d}")}</div>
  <h2 class="headline">{rich(s.get("title"))}</h2>
  <p class="body">{rich(s.get("body"))}</p>
</div>'''
    elif lay == "stat":
        inner = DIAG.format(cls=" small") + f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <div class="value">{esc(s.get("value"))}</div>
  <div class="label">{rich(s.get("label"))}</div>
  <div class="source">Fuente: {esc(s.get("source"))}</div>
</div>'''
    elif lay == "list":
        items = "".join(f"<li>{CHECK}<span>{rich(x)}</span></li>" for x in s.get("items", []))
        inner = DIAG.format(cls=" small") + f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <h2 class="headline">{rich(s.get("title"))}</h2><ul>{items}</ul>
</div>'''
    elif lay == "quote":
        inner = DIAG.format(cls=" small") + f'''<div class="copy">
  <div class="mark">“</div><h2 class="headline">{rich(s.get("text"))}</h2>
  {f'<div class="who">{esc(s.get("author"))}</div>' if s.get("author") else ''}
</div>'''
    elif lay == "closing":
        inner = DIAG.format(cls=" small") + f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <h2 class="headline">{rich(s.get("headline"))}</h2>
  {f'<p class="body">{rich(s.get("body"))}</p>' if s.get("body") else ''}
  {f'<div class="cta">{esc(s.get("cta"))}</div>' if s.get("cta") else ''}
</div>
<div class="valox"><div class="q">¿Tienes dudas sobre la seguridad de tu empresa?</div>
<div class="a">Pregúntale a <b>Valox</b>, nuestro agente de IA en ciberseguridad, disponible 24/7.</div></div>'''
    else:
        raise SystemExit(f"Layout desconocido en slide {i}: {lay}")
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="{BRAND}/brand.css"></head>
<body><div class="slide l-{lay}">{inner}{foot(i, n, lay)}</div></body></html>'''


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    post_dir = pathlib.Path(sys.argv[1]).resolve()
    spec = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    slides = spec["slides"]
    out = post_dir / "slides"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    from playwright.sync_api import sync_playwright
    paths = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, s in enumerate(slides, 1):
            f = pathlib.Path(tmp) / f"{i:02d}.html"
            f.write_text(slide_html(s, i, len(slides)), encoding="utf-8")
            pg.goto(f.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            overflow = pg.evaluate("""() => [...document.querySelectorAll('.copy')].some(c => {
                const r = c.getBoundingClientRect();
                const lim = Math.min(...[...document.querySelectorAll('.foot, .valox')].map(e => e.getBoundingClientRect().top));
                return r.bottom > lim - 24 || r.top < 150 || r.right > 1080 - 90; })""")
            dest = out / f"{i:02d}.png"
            pg.screenshot(path=str(dest), clip={"x": 0, "y": 0, "width": W, "height": H})
            paths.append(dest)
            print(f"slide {i:02d} ({s.get('layout')}) -> {dest.relative_to(ROOT)}" + ("  ⚠ TEXTO DEMASIADO LARGO: se monta sobre el pie" if overflow else ""))
        b.close()
    if spec.get("network") == "linkedin" and spec.get("format") == "document":
        from PIL import Image
        imgs = [Image.open(x).convert("RGB") for x in paths]
        pdf = post_dir / "document.pdf"
        imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=144)
        print(f"PDF -> {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Renderiza las slides de un post VALCOM a PNG 1080x1350 (y PDF si es documento de LinkedIn).

Uso:  python3 scripts/render.py posts/2026/10/2026-10-21_slug
Requiere: pip install playwright pillow && python3 -m playwright install chromium

Marcado en textos: *texto* en headline -> dorado; **texto** en body -> dorado.

Imágenes: cualquier slide acepta "image": {"file": "images/x.jpg", "mode": "full"|"band"|"hero", "brief": "..."}.
  full = foto a sangre detrás del texto (cover, quote, closing); band = franja de foto bajo el logo (stat, point, list); hero = logo/captura a color bajo el logo (portada).
  Si el archivo no existe se dibuja un marcador "IMAGEN PENDIENTE" con el brief, y check.py bloquea la publicación.
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


CHECK = '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#C9B497" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l4 4 10-10"/></svg>'


def head(i, n, kind):
    """Logo oficial (archivo real, nunca redibujado) arriba a la izquierda; nada más en la cabecera."""
    return f'<div class="head"><img class="logo" src="{BRAND}/logos/valcom-logo-horizontal.png" alt="VALCOM"></div>'


def foot(i, n, kind):
    if kind == "cover":
        right = '<div class="swipe">Desliza →</div>' if n > 1 else '<div class="meta"></div>'
    elif kind == "closing":
        right = '<div class="page"></div>'
    else:
        right = f'<div class="page">{i:02d} / {n:02d}</div>'
    return f'<div class="foot"><div class="web">www.valcomsa.com</div>{right}</div>'


POST_DIR = None

# Valox es opcional: solo aparece si la slide de cierre lleva "valox": true en post.json
VALOX_BLOCK = '''<div class="valox"><div class="q">¿Tienes dudas sobre la seguridad de tu empresa?</div>
<div class="a">Pregúntale a <b>Valox</b>, nuestro agente de IA en ciberseguridad, disponible 24/7.</div></div>'''


def image_html(s):
    img = s.get("image")
    if not img:
        return "", ""
    mode = img.get("mode") or ("full" if s.get("layout") in ("cover", "quote", "closing") else "band")
    f = (POST_DIR / img.get("file", "")) if img.get("file") else None
    if f and f.exists():
        pos = esc(img.get("position", "50% 50%"))
        tag = f'<div class="ph ph-{mode}"><img src="{f.as_uri()}" style="object-position:{pos}" alt=""></div>'
    else:
        tag = (f'<div class="ph ph-{mode} ph-missing"><div class="ph-msg"><b>IMAGEN PENDIENTE</b>'
               f'<span>{esc(img.get("brief", ""))}</span><i>{esc(img.get("file", ""))}</i></div></div>')
    return tag, f" has-{mode}"


def slide_html(s, i, n):
    lay = s.get("layout", "cover")
    if lay == "cover":
        inner = f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <h1 class="headline">{rich(s.get("headline"))}</h1>
  {f'<p class="body">{rich(s.get("body"))}</p>' if s.get("body") else ''}
</div>'''
    elif lay == "point":
        inner = f'''<div class="copy">
  <div class="num">{esc(s.get("number") or f"{i-1:02d}")}</div>
  <h2 class="headline">{rich(s.get("title"))}</h2>
  <p class="body">{rich(s.get("body"))}</p>
</div>'''
    elif lay == "stat":
        inner = f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <div class="value">{esc(s.get("value"))}</div>
  <div class="label">{rich(s.get("label"))}</div>
  <div class="source">Fuente: {esc(s.get("source"))}</div>
</div>'''
    elif lay == "list":
        items = "".join(f"<li>{CHECK}<span>{rich(x)}</span></li>" for x in s.get("items", []))
        inner = f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <h2 class="headline">{rich(s.get("title"))}</h2><ul>{items}</ul>
</div>'''
    elif lay == "quote":
        inner = f'''<div class="copy">
  <div class="mark">“</div><h2 class="headline">{rich(s.get("text"))}</h2>
  {f'<div class="who">{esc(s.get("author"))}</div>' if s.get("author") else ''}
</div>'''
    elif lay == "closing":
        inner = f'''<div class="copy">
  {f'<div class="eyebrow">{esc(s.get("eyebrow"))}</div>' if s.get("eyebrow") else ''}
  <h2 class="headline">{rich(s.get("headline"))}</h2>
  {f'<p class="body">{rich(s.get("body"))}</p>' if s.get("body") else ''}
  {f'<div class="cta">{esc(s.get("cta"))}</div>' if s.get("cta") else ''}
</div>
{VALOX_BLOCK if s.get("valox") else ""}'''
    else:
        raise SystemExit(f"Layout desconocido en slide {i}: {lay}")
    ph, cls = image_html(s)
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="{BRAND}/brand.css"></head>
<body><div class="slide l-{lay}{cls}">{ph}{head(i, n, lay)}{inner}{foot(i, n, lay)}</div></body></html>'''


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    global POST_DIR
    post_dir = pathlib.Path(sys.argv[1]).resolve()
    POST_DIR = post_dir
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
                const hd = document.querySelector('.head').getBoundingClientRect();
                return r.bottom > lim - 24 || r.top < hd.bottom + 24 || r.right > 1080 - 90; })""")
            dest = out / f"{i:02d}.png"
            pg.screenshot(path=str(dest), clip={"x": 0, "y": 0, "width": W, "height": H})
            paths.append(dest)
            img = s.get("image") or {}
            missing = img and not (img.get("file") and (post_dir / img["file"]).exists())
            print(f"slide {i:02d} ({s.get('layout')}) -> {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}"
                  + ("  ⚠ TEXTO DEMASIADO LARGO: se monta sobre el pie" if overflow else "")
                  + (f"  ⚠ IMAGEN PENDIENTE: {img.get('file')} — pedírsela al usuario" if missing else ""))
        b.close()
    if spec.get("network") == "linkedin" and spec.get("format") == "document":
        from PIL import Image
        imgs = [Image.open(x).convert("RGB") for x in paths]
        pdf = post_dir / "document.pdf"
        imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=144)
        print(f"PDF -> {pdf.relative_to(ROOT) if pdf.is_relative_to(ROOT) else pdf}")


if __name__ == "__main__":
    main()

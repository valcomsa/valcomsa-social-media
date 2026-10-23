#!/usr/bin/env python3
"""Valida un post antes de subirlo a Buffer. Sale con código 1 si hay errores.

Uso:  python3 scripts/check.py posts/2026/10/2026-10-21_slug
      python3 scripts/check.py --add-forbidden "nombre del aliado"
"""
import datetime, hashlib, json, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORBIDDEN = ROOT / "brand" / "forbidden.sha256"
VALOX_URL = "https://lnkd.in/eNA2SkUj"

RULES = {
    "instagram": {"caption_max": 2200, "hashtags_max": 5, "slides_max": 10, "hook": 125},
    "linkedin": {"caption_max": 3000, "hashtags_max": 3, "slides_max": 20, "hook": 140},
}
LAYOUTS = {"cover", "point", "stat", "list", "quote", "closing"}


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def forbidden_hits(text):
    hashes = {l.strip() for l in FORBIDDEN.read_text().splitlines() if l.strip() and not l.startswith("#")}
    words = re.findall(r"[a-z0-9]+", norm(text))
    hits = []
    for n in range(1, 5):
        for i in range(len(words) - n + 1):
            for joiner in (" ", "", "-"):
                if h(joiner.join(words[i:i + n])) in hashes:
                    hits.append(" ".join(words[i:i + n]))
    return sorted(set(hits))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--add-forbidden":
        t = norm(sys.argv[2]).strip()
        with FORBIDDEN.open("a") as f:
            f.write(h(t) + "\n")
        print("Agregado (solo el hash, el término no queda en el repo).")
        return
    post = pathlib.Path(sys.argv[1]).resolve()
    spec = json.loads((post / "post.json").read_text(encoding="utf-8"))
    caption = (post / "caption.md").read_text(encoding="utf-8").strip() if (post / "caption.md").exists() else ""
    E, W = [], []

    reel = spec.get("format") == "reel"
    for k in (("id", "network", "format", "publish_at", "status", "alt_text") if reel else ("id", "network", "format", "publish_at", "status", "slides", "alt_text")):
        if k not in spec:
            E.append(f"post.json sin campo '{k}'")
    net = spec.get("network")
    if net not in RULES:
        raise SystemExit(f"network debe ser instagram o linkedin, no {net!r}")
    r = RULES[net]
    fmt = spec.get("format")
    ok_fmt = {"instagram": {"single", "carousel", "reel"}, "linkedin": {"single", "carousel", "document"}}[net]
    if fmt not in ok_fmt:
        E.append(f"format '{fmt}' no válido para {net}: {sorted(ok_fmt)}")
    if spec.get("id") != post.name:
        E.append(f"id ({spec.get('id')}) debe ser igual al nombre de la carpeta ({post.name})")

    if reel:
        check_reel(post, spec, caption, E, W)
        return finish(post, spec, caption, r, net, E, W)
    slides = spec.get("slides", [])
    n = len(slides)
    if n == 0:
        E.append("No hay slides")
    if fmt == "single" and n != 1:
        E.append("format single requiere exactamente 1 slide")
    if fmt in ("carousel", "document") and n < 3:
        E.append("Un carrusel o documento necesita al menos 3 slides")
    if n > r["slides_max"]:
        E.append(f"{net} vía Buffer admite máximo {r['slides_max']} imágenes; hay {n}")
    if net == "instagram" and fmt == "carousel" and 4 <= n <= 7:
        W.append(f"Carrusel de {n} slides: el engagement cae entre 4 y 7 (Socialinsider). Recorta a 3 o desarrolla hasta 8–10")
    if net == "linkedin" and fmt == "document" and n < 5:
        W.append(f"Documento de {n} páginas: por debajo de 5 rinde como una imagen; usa format single o desarrolla hasta 8–10")
    if net == "linkedin" and fmt == "document" and n > 12:
        W.append(f"Documento de {n} páginas: la lectura cae después de ~12; recorta a 8–10")
    for i, s in enumerate(slides, 1):
        if s.get("layout") not in LAYOUTS:
            E.append(f"slide {i}: layout '{s.get('layout')}' no existe ({sorted(LAYOUTS)})")
        if s.get("layout") == "stat" and not s.get("source"):
            E.append(f"slide {i}: una cifra sin fuente no se publica")
        img = s.get("image")
        if img and s.get("layout") == "closing":
            E.append(f"slide {i}: el cierre no lleva imagen (compite con el CTA y Valox)")
        if img:
            f = post / img.get("file", "") if img.get("file") else None
            if not f or not f.exists():
                E.append(f"slide {i}: IMAGEN PENDIENTE ({img.get('file')}). Pídesela al usuario con este brief: {img.get('brief', '(sin brief)')}")
            else:
                from PIL import Image as _I
                w, h = _I.open(f).size
                need = 1080 if (img.get("mode") or "full") == "full" else 888
                if w < need:
                    W.append(f"slide {i}: la imagen mide {w}x{h}; para nitidez conviene ≥ {need} px de ancho")
            if str(img.get("rights", "")).upper().startswith("PENDIENTE"):
                E.append(f"slide {i}: derechos de la imagen sin confirmar ({img.get('file')}): no se publica hasta saber si es propia o tiene licencia comercial")
            elif not img.get("rights"):
                W.append(f"slide {i}: falta 'rights' en la imagen (propia, licenciada o banco con licencia comercial)")
    if n > 1 and slides[-1].get("layout") != "closing":
        E.append("La última slide de un carrusel/documento debe ser 'closing' (cierre con Valox)")
    if n and slides[0].get("layout") not in ("cover", "stat", "quote"):
        W.append("La primera slide debería ser cover, stat o quote: es el gancho")
    alts = spec.get("alt_text", [])
    if len(alts) != n or any(not a.strip() for a in alts):
        E.append(f"alt_text debe tener un texto por slide ({n}); tiene {len(alts)}")

    return finish(post, spec, caption, r, net, E, W)


def check_reel(post, spec, caption, E, W):
    import subprocess
    mp4 = post / "reel.mp4"
    if not (post / "reel.html").exists():
        E.append("Falta reel.html")
    if not mp4.exists():
        E.append("Falta reel.mp4: corre scripts/render_reel.py")
        return
    if not (post / "cover.jpg").exists():
        E.append("Falta cover.jpg: corre scripts/render_reel.py")
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,codec_name,r_frame_rate:format=duration", "-of", "json", str(mp4)],
                         capture_output=True, text=True)
    info = json.loads(out.stdout or "{}")
    st = (info.get("streams") or [{}])[0]
    dur = float(info.get("format", {}).get("duration", 0))
    if (st.get("width"), st.get("height")) != (1080, 1920):
        E.append(f"reel.mp4 mide {st.get('width')}x{st.get('height')}; debe ser 1080x1920")
    if st.get("codec_name") != "h264":
        E.append("reel.mp4 debe ser H.264")
    if not 3 <= dur <= 90:
        E.append(f"Duración {dur:.1f}s: un Reel vía Buffer debe durar entre 3 y 90 s")
    elif dur > 45:
        W.append(f"Duración {dur:.1f}s: para motion sin voz conviene 15–35 s")
    if mp4.stat().st_size > 100 * 1024 * 1024:
        E.append("reel.mp4 pesa más de 100 MB (límite de GitHub)")
    if len(spec.get("alt_text", [])) != 1:
        E.append("alt_text de un reel: una sola descripción del video")
    if not spec.get("sources"):
        E.append("Un reel con datos debe listar sus fuentes en post.json.sources")


def finish(post, spec, caption, r, net, E, W):
    if not caption:
        E.append("Falta caption.md")
    if len(caption) > r["caption_max"]:
        E.append(f"Caption de {len(caption)} caracteres; máximo {r['caption_max']} en {net}")
    tags = re.findall(r"(?<!\w)#\w+", caption)
    if len(tags) > r["hashtags_max"]:
        E.append(f"{len(tags)} hashtags; máximo {r['hashtags_max']} en {net}")
    if "valox" not in caption.lower():
        E.append("El caption debe cerrar con la mención a Valox")
    if net == "instagram" and VALOX_URL not in caption:
        W.append("El cierre de Valox en Instagram lleva el enlace " + VALOX_URL + " (no es clicable en el caption; también va en la bio)")
    first = caption.split("\n", 1)[0]
    if len(first) > r["hook"]:
        W.append(f"La primera línea tiene {len(first)} caracteres; se corta en ~{r['hook']}. El gancho debe caber antes del 'más'")
    if net == "linkedin" and re.search(r"https?://", caption.replace(VALOX_URL, "")):
        W.append("Enlace externo en el caption de LinkedIn: reduce el alcance. Mejor en un comentario o sin enlace")
    if net == "linkedin" and len(caption) > 1600:
        W.append(f"Texto de {len(caption)} caracteres: para LinkedIn VALCOM apunta a 800–1.300 (poco texto, mucho impacto)")
    if re.search(r"(US)?\$\s?\d|\bUSD\s?\d", caption):
        W.append("Aparecen montos: VALCOM no publica precios (primero evalúa, después cotiza)")

    all_text = caption + " " + json.dumps(spec, ensure_ascii=False)
    hits = forbidden_hits(all_text)
    if hits:
        E.append("Contiene un nombre de aliado/subcontratista prohibido en contenido público (" + str(len(hits)) + " coincidencia/s)")

    try:
        due = datetime.datetime.fromisoformat(spec.get("publish_at", ""))
        if due.tzinfo is None:
            E.append("publish_at necesita zona horaria, p. ej. 2026-10-21T09:00:00-05:00")
        elif spec.get("status") in ("draft", "ready") and due <= datetime.datetime.now(datetime.timezone.utc):
            E.append("publish_at ya pasó")
    except ValueError:
        E.append("publish_at no es ISO 8601")

    if spec.get("format") == "reel":
        return report(post, E, W)
    n = len(spec.get("slides", []))
    fmt = spec.get("format")
    pngs = sorted((post / "slides").glob("*.png")) if (post / "slides").exists() else []
    if len(pngs) != n:
        E.append(f"Hay {len(pngs)} PNG en slides/ y {n} slides en post.json: corre scripts/render.py")
    else:
        from PIL import Image
        for p in pngs:
            im = Image.open(p)
            if im.size != (1080, 1350):
                E.append(f"{p.name} mide {im.size}; debe ser 1080x1350")
            if p.stat().st_size > 8 * 1024 * 1024:
                E.append(f"{p.name} pesa más de 8 MB")
    if fmt == "document" and not (post / "document.pdf").exists():
        E.append("Falta document.pdf: corre scripts/render.py")
    return report(post, E, W)


def report(post, E, W):
    for w in W:
        print("AVISO  ", w)
    for e in E:
        print("ERROR  ", e)
    print(f"{'OK' if not E else 'FALLA'}: {len(E)} errores, {len(W)} avisos — {post.name}")
    sys.exit(1 if E else 0)


if __name__ == "__main__":
    main()

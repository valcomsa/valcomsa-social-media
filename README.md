# VALCOM — contenido de redes sociales

Repositorio público de donde Buffer toma las imágenes y documentos que publica en Instagram (`valcom.sa`) y LinkedIn (`Valcom S.A.`). Todo lo que se sube aquí es visible para cualquiera **antes** de su fecha de publicación: no subir borradores con información interna.

## Estructura

```
brand/            tokens del design system VALCOM, fuentes (OFL), logos oficiales, términos prohibidos (hash)
scripts/          new_post.py · render.py · check.py · buffer_payload.py
posts/AAAA/MM/    una carpeta por post: AAAA-MM-DD_slug-ig | AAAA-MM-DD_slug-li
examples/         un carrusel de Instagram y un documento de LinkedIn de referencia
buffer.json       organización y canales de Buffer
```

Cada carpeta de post contiene:

| Archivo | Qué es |
| --- | --- |
| `post.json` | red, formato, fecha y hora de publicación (con zona `-05:00`), estado, slides, textos alternativos, fuentes, id del post en Buffer |
| `caption.md` | el copy exacto que se publica |
| `slides/01.png …` | imágenes 1080×1350 (4:5) generadas por `render.py` |
| `document.pdf` | solo LinkedIn formato `document`: las slides en un PDF |
| `reel.html` · `reel.mp4` · `cover.jpg` | solo formato `reel`: animación (motor `brand/reel.js`), video 1080×1920 y portada, generados por `render_reel.py` |

Estados en `post.json`: `draft` → `ready` (pasó `check.py`) → `scheduled` (está en Buffer, con `buffer.post_id`) → `published`.

## Flujo

```bash
pip install -r requirements.txt && python3 -m playwright install chromium
python3 scripts/new_post.py instagram carousel 2026-10-21 ransomware-cuando 09:00
# editar post.json y caption.md
python3 scripts/render.py posts/2026/10/2026-10-21_ransomware-cuando-ig
python3 scripts/check.py  posts/2026/10/2026-10-21_ransomware-cuando-ig
git add posts/... && git commit -m "IG 2026-10-21 ransomware-cuando" && git push
python3 scripts/buffer_payload.py posts/2026/10/2026-10-21_ransomware-cuando-ig   # argumentos para Buffer create_post
```

Las URLs que recibe Buffer apuntan al commit (`raw.githubusercontent.com/valcomsa/valcomsa-social-media/<sha>/…`), así que no se rompen si el archivo cambia después. Buffer descarga la imagen al momento de publicar: el repo debe seguir siendo público y los archivos no deben borrarse del historial.

## Reglas que verifica `check.py`

- Instagram: 1 a 10 imágenes, caption ≤ 2.200 caracteres, máximo 5 hashtags.
- LinkedIn: caption ≤ 3.000 caracteres, máximo 3 hashtags, documento de 5 a 12 páginas recomendado.
- Toda slide con cifra lleva fuente; todo carrusel termina en slide de cierre con Valox; un texto alternativo por imagen.
- El caption menciona a Valox. Avisa si hay montos (VALCOM no publica precios) o enlaces externos en LinkedIn.
- Bloquea nombres de aliados y subcontratistas (guardados como hash en `brand/forbidden.sha256`; agregar con `python3 scripts/check.py --add-forbidden "nombre"`).

Fuentes: Inter y Playfair Display, licencia SIL Open Font License (`brand/fonts/OFL-*.txt`). Logos © VALCOM S.A., uso exclusivo de la marca.

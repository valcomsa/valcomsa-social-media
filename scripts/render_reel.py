#!/usr/bin/env python3
"""Renderiza un Reel VALCOM (motion sin voz) a MP4 1080x1920, H.264, 30 fps.

Uso:  python3 scripts/render_reel.py posts/AAAA/MM/<id> [--preview] [--silent]

La carpeta del post contiene reel.html, que:
  - usa {{BRAND}} para referirse a la carpeta brand/ (fuentes, brand.css, logos, reel.js)
  - define window.REEL = {duration: segundos, fps: 30, cover: segundo_del_frame_de_portada}
  - define window.renderAt(t): pinta el frame del segundo t (determinista, sin animaciones CSS)
Salida: reel.mp4, cover.jpg (frame de portada) y contact.jpg (hoja de contacto para revisión).
Si existe audio.wav en la carpeta se mezcla; si no, se genera una pista sutil de pulso/tic (sin voz).
--preview renderiza a 10 fps para revisar rápido. --silent no agrega audio.
"""
import json, math, pathlib, struct, subprocess, sys, tempfile, wave

ROOT = pathlib.Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
W, H = 1080, 1920


def make_audio(path, duration, beats):
    """Pista sutil: pulso grave + tic de reloj cada segundo + impacto en cada cambio de escena."""
    sr = 48000
    n = int(sr * duration)
    buf = [0.0] * n
    for i in range(n):
        t = i / sr
        buf[i] += 0.035 * math.sin(2 * math.pi * 55 * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.5 * t))
    def add(at, dur, f, amp, decay):
        s = int(at * sr)
        for j in range(int(dur * sr)):
            if s + j >= n:
                break
            tt = j / sr
            buf[s + j] += amp * math.exp(-tt * decay) * math.sin(2 * math.pi * f * tt)
    for sec in range(int(duration)):
        add(sec + 0.0, 0.03, 2400, 0.10, 180)
        add(sec + 0.0, 0.03, 1200, 0.06, 160)
    for b in beats:
        add(b, 0.6, 48, 0.55, 7)
        add(b, 0.25, 96, 0.20, 14)
    peak = max(abs(x) for x in buf) or 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(32767 * 0.85 * x / peak)) for x in buf))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    post = pathlib.Path(sys.argv[1]).resolve()
    preview = "--preview" in sys.argv
    html = (post / "reel.html").read_text(encoding="utf-8").replace("{{BRAND}}", BRAND.as_uri())
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        page_file = tmp / "reel.html"
        page_file.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(page_file.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(300)
            meta = pg.evaluate("window.REEL")
            dur, fps = float(meta["duration"]), int(meta.get("fps", 30))
            if preview:
                fps = 10
            beats = meta.get("beats", [])
            out = post / ("reel-preview.mp4" if preview else "reel.mp4")
            silent = "--silent" in sys.argv
            audio = post / "audio.wav"
            if not silent and not audio.exists():
                gen = tmp / "audio.wav"
                make_audio(gen, dur, beats)
                audio = gen
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-"]
            if not silent:
                cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "160k", "-shortest"]
            cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
                    "-r", "30", "-movflags", "+faststart", str(out)]
            ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            total = int(round(dur * fps))
            for i in range(total):
                pg.evaluate("t => window.renderAt(t)", i / fps)
                ff.stdin.write(pg.screenshot(type="jpeg", quality=95))
                if i % (fps * 5) == 0:
                    print(f"  {i / fps:5.1f}s / {dur:.1f}s", flush=True)
            ff.stdin.close()
            if ff.wait() != 0:
                raise SystemExit("ffmpeg falló")
            pg.evaluate("t => window.renderAt(t)", float(meta.get("cover", 0.5)))
            pg.screenshot(path=str(post / "cover.jpg"), type="jpeg", quality=92)
            shots = []
            for k in range(12):
                tt = dur * (k + 0.5) / 12
                pg.evaluate("t => window.renderAt(t)", tt)
                f = tmp / f"c{k:02d}.jpg"
                pg.screenshot(path=str(f), type="jpeg", quality=80)
                shots.append(f)
            b.close()
        from PIL import Image
        thumbs = [Image.open(s).resize((270, 480)) for s in shots]
        sheet = Image.new("RGB", (270 * 6 + 50, 480 * 2 + 10), (255, 255, 255))
        for k, im in enumerate(thumbs):
            sheet.paste(im, ((k % 6) * 280, (k // 6) * 490))
        sheet.save(post / "contact.jpg", quality=85)
    if errors:
        print("ERRORES JS:", *errors, sep="\n  ")
    size = out.stat().st_size / 1e6
    print(f"OK -> {out.relative_to(ROOT)} ({dur:.1f}s, {size:.1f} MB), cover.jpg, contact.jpg")


if __name__ == "__main__":
    main()

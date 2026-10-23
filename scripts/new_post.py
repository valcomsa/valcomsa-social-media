#!/usr/bin/env python3
"""Crea la carpeta de un post nuevo con post.json y caption.md de plantilla.

Uso:  python3 scripts/new_post.py instagram|linkedin single|carousel|document 2026-10-21 slug-corto [09:00]
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
net, fmt, date, slug = sys.argv[1:5]
hour = sys.argv[5] if len(sys.argv) > 5 else "09:00"
pid = f"{date}_{slug}"
d = ROOT / "posts" / date[:4] / date[5:7] / f"{pid}-{'ig' if net == 'instagram' else 'li'}"
pid = d.name
d.mkdir(parents=True, exist_ok=False)
REEL_REF = ROOT / "posts" / "2026" / "10" / "2026-10-26_php2shell-ig" / "reel.html"
slides = [{"layout": "cover", "eyebrow": "", "headline": "", "body": ""}]
if fmt != "single":
    slides += [{"layout": "point", "title": "", "body": ""}, {"layout": "closing", "headline": "", "body": "", "cta": "Agenda una evaluación"}]
spec = {"id": pid, "network": net, "format": fmt, "publish_at": f"{date}T{hour}:00-05:00", "status": "draft",
        "pillar": "", "campaign": "", "title": "", "first_comment": "", "slides": slides,
        "alt_text": ["" for _ in slides], "sources": [], "buffer": {"post_id": "", "scheduled_at": ""}}
if fmt == "reel":
    spec.pop("slides"); spec["alt_text"] = [""]; spec["cover_time"] = 1.0
    if REEL_REF.exists():
        (d / "reel.html").write_text(REEL_REF.read_text(encoding="utf-8"), encoding="utf-8")
(d / "post.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(d / "caption.md").write_text("", encoding="utf-8")
print(d.relative_to(ROOT))

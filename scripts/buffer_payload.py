#!/usr/bin/env python3
"""Arma los argumentos para la herramienta create_post de Buffer a partir de un post ya subido a GitHub.

Uso:  python3 scripts/buffer_payload.py posts/2026/10/2026-10-21_slug [--mode customScheduled|addToQueue|shareNow] [--draft]

Las URLs apuntan al commit actual (raw.githubusercontent.com/<org>/<repo>/<sha>/...): son estables aunque
el archivo cambie después. Correr SOLO después de git push, y verificar que cada URL responde 200.
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "buffer.json").read_text(encoding="utf-8"))


def git(*a):
    return subprocess.check_output(["git", "-C", str(ROOT), *a], text=True).strip()


def main():
    post = pathlib.Path(sys.argv[1]).resolve()
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "customScheduled"
    spec = json.loads((post / "post.json").read_text(encoding="utf-8"))
    caption = (post / "caption.md").read_text(encoding="utf-8").strip()
    sha = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--", str(post.relative_to(ROOT))):
        raise SystemExit("Hay cambios sin commit en este post: commit + push primero.")
    if git("rev-parse", "HEAD") != git("rev-parse", "@{u}"):
        raise SystemExit("El commit local no está en GitHub: git push primero.")
    base = f"https://raw.githubusercontent.com/{CFG['repo']}/{sha}/"
    rel = post.relative_to(ROOT).as_posix()
    pngs = sorted((post / "slides").glob("*.png"))
    net = spec["network"]
    args = {"channelId": CFG["channels"][net]["id"], "schedulingType": "automatic", "mode": mode, "text": caption}
    if mode == "customScheduled":
        args["dueAt"] = spec["publish_at"]
    if "--draft" in sys.argv:
        args["saveToDraft"] = True
    if net == "linkedin" and spec["format"] == "document":
        args["assets"] = [{"document": {"url": base + rel + "/document.pdf", "title": spec.get("title") or spec["id"],
                                        "thumbnailUrl": base + rel + "/slides/01.png"}}]
    else:
        args["assets"] = [{"image": {"url": base + rel + "/slides/" + p.name, "metadata": {"altText": alt}}}
                          for p, alt in zip(pngs, spec["alt_text"])]
    md = {}
    if net == "instagram":
        md["instagram"] = {"type": "post", "shouldShareToFeed": True}
        if spec.get("first_comment"):
            md["instagram"]["firstComment"] = spec["first_comment"]
    elif spec.get("first_comment"):
        md["linkedin"] = {"firstComment": spec["first_comment"]}
    if md:
        args["metadata"] = md
    print(json.dumps(args, ensure_ascii=False, indent=2))
    urls = [a.get("image", a.get("document", {})).get("url") for a in args["assets"]]
    if net == "linkedin" and spec["format"] == "document":
        urls.append(args["assets"][0]["document"]["thumbnailUrl"])
    print("\n# Verificar antes de llamar a Buffer:", file=sys.stderr)
    for u in urls:
        print(f"curl -sI '{u}' | head -1", file=sys.stderr)


if __name__ == "__main__":
    main()

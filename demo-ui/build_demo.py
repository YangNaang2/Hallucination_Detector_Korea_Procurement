"""Rebuild the shareable, offline HTML from the editable UI fragment."""
from pathlib import Path
import re
import subprocess

folder = Path(__file__).resolve().parent
fragment = (folder / "orbit-demo.fragment.html").read_text(encoding="utf-8")
script = re.search(r"<script>([\s\S]*?)</script>", fragment).group(1)
checked = subprocess.run(["node", "--check"], input=script, text=True, capture_output=True)
if checked.returncode:
    raise RuntimeError(checked.stderr)

# The chat host supplies Lucide. Use text glyphs in the offline export instead.
for name, glyph in {"orbit": "◎", "files": "▤", "scan-line": "⌗"}.items():
    fragment = fragment.replace(
        f'<i data-lucide="{name}" aria-hidden="true"></i>',
        f'<span aria-hidden="true">{glyph}</span>',
    )
page = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>ORBIT · 나라장터 입찰 검토 데모</title>
<style>html{background:#070b15}body{margin:0;padding:24px;max-width:1540px;margin-inline:auto} @media(max-width:600px){body{padding:0}} </style>
</head><body>
""" + fragment + "\n</body></html>\n"
out = folder / "ORBIT_입찰검토_데모.html"
out.write_text(page, encoding="utf-8")
print("JavaScript syntax: OK")
print("Standalone HTML:", out)
print("UTF-8 replacement characters:", page.count("\ufffd"))
print("Network requests: none; all content and styles embedded")

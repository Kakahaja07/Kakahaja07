#!/usr/bin/env python3
"""
One-time helper: shrinks the two custom fonts and records exact text widths.

  python scripts/make_fonts.py <Geomini.woff2> <UncutSans_Variable.ttf>

Needs `pip install fonttools brotli`. Writes into scripts/fonts/:
  geomini.woff2, uncut-sans.woff2  - Latin subsets that build_profile.py embeds in every card
  metrics.json                     - glyph widths so the card layout needs no font tools

build_profile.py itself uses only the standard library, so the daily Action does not
need this script or those packages.
"""
import io, json, sys
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).resolve().parent / "fonts"
CHARS = list(range(0x20, 0x7F)) + [0x2014, 0x2013, 0xB7, 0x2019, 0x2018, 0x201C, 0x201D, 0x2026, 0x2022, 0xD7]


def load(path, pin):
    f = TTFont(path)
    if not pin:
        return f
    buf = io.BytesIO()                      # round-trip so the subsetter sees fully loaded tables
    instancer.instantiateVariableFont(f, pin).save(buf)
    buf.seek(0)
    return TTFont(buf)


def shrink(font, name):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=CHARS)
    sub.subset(font)
    OUT.mkdir(exist_ok=True)
    font.flavor = "woff2"
    font.save(OUT / name)
    print(name, (OUT / name).stat().st_size, "bytes")


def widths(path, pin, weight):
    f = instancer.instantiateVariableFont(TTFont(path), {**pin, "wght": weight})
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    return {chr(c): hmtx[cmap[c]][0] for c in CHARS if c in cmap}


def main(geo, uncut):
    metrics = {"upm": 1000, "geomini": {}, "uncut": {}}
    shrink(load(geo, {}), "geomini.woff2")
    shrink(load(uncut, {"ital": 0}), "uncut-sans.woff2")
    for w in (500, 600, 700):
        metrics["geomini"][str(w)] = widths(geo, {}, w)
    for w in (400, 500, 600):
        metrics["uncut"][str(w)] = widths(uncut, {"ital": 0}, w)
    (OUT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("metrics.json written")


if __name__ == "__main__":
    main(*sys.argv[1:3])

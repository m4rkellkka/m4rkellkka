"""Draw the roof cat as smooth shapes, then reduce it to the pixel grids in build_profile.CAT_ART.

    python3 scripts/profile/make_cat_art.py cat.json
"""
# Draw smooth cat shapes at 10x, then reduce to a pixel grid with a 1px outline.
import json, sys
from PIL import Image, ImageDraw
O, W, P, E = (210, 122, 56), (244, 232, 214), (234, 154, 150), (40, 24, 16)
CELL = 8

def make(w, h, draw_fn):
    art = Image.new("RGB", (w * CELL, h * CELL), (0, 0, 0))
    draw_fn(ImageDraw.Draw(art))
    w, h = w + 2, h + 2  # a cell of margin on every side, so the outline always fits
    im = Image.new("RGB", (w * CELL, h * CELL), (0, 0, 0))
    im.paste(art, (CELL, CELL))
    names = {O: "O", W: "W", P: "P", E: "E"}
    grid = []
    for gy in range(h):
        row = []
        for gx in range(w):
            counts = {}
            for yy in range(gy * CELL + 1, gy * CELL + CELL, 2):
                for xx in range(gx * CELL + 1, gx * CELL + CELL, 2):
                    px = im.getpixel((xx, yy))
                    counts[px] = counts.get(px, 0) + 1
            filled = {k: v for k, v in counts.items() if k != (0, 0, 0)}
            total = sum(counts.values())
            if sum(filled.values()) * 2 < total:
                row.append(".")
            else:
                # eyes/nose win if present at all, so tiny features survive the reduction
                for feat in (E, P):
                    if filled.get(feat, 0) >= 4:
                        row.append(names[feat]); break
                else:
                    row.append(names[max(filled, key=filled.get)])
        grid.append(row)
    # 1px outline around the silhouette
    out = [r[:] for r in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] != ".":
                continue
            if any(0 <= y + dy < h and 0 <= x + dx < w and grid[y + dy][x + dx] != "." for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = "K"
    return ["".join(r).replace("E", "K") for r in out]

def sit(d):
    d.ellipse((40, 92, 140, 178), fill=O)                      # body
    d.line([(52, 168), (26, 166), (16, 146), (22, 126)], fill=O, width=15, joint="curve")  # tail
    d.ellipse((14, 116, 30, 132), fill=O)
    d.rectangle((96, 140, 112, 176), fill=O); d.rectangle((120, 140, 136, 176), fill=O)  # front legs
    d.ellipse((104, 96, 140, 150), fill=W)                      # chest
    d.ellipse((92, 168, 116, 180), fill=W); d.ellipse((118, 168, 142, 180), fill=W)       # paws
    d.ellipse((76, 34, 156, 102), fill=O)                       # head
    d.polygon([(80, 56), (84, 12), (110, 40)], fill=O); d.polygon([(124, 38), (150, 10), (154, 58)], fill=O)  # ears
    d.polygon([(89, 40), (89, 26), (98, 36)], fill=P); d.polygon([(136, 34), (145, 24), (145, 40)], fill=P)
    d.ellipse((102, 72, 136, 96), fill=W)                       # muzzle
    d.rectangle((100, 58, 109, 69), fill=E); d.rectangle((128, 58, 137, 69), fill=E)      # eyes
    d.rectangle((115, 72, 122, 78), fill=P)                     # nose

def jump(d):
    d.ellipse((30, 60, 150, 112), fill=O)                       # stretched body
    d.line([(40, 80), (18, 60), (10, 32)], fill=O, width=14, joint="curve")              # tail up
    d.ellipse((4, 22, 18, 36), fill=O)
    d.polygon([(136, 92), (176, 116), (168, 126), (124, 106)], fill=O)                   # front legs forward
    d.polygon([(48, 96), (14, 124), (24, 132), (64, 106)], fill=O)                       # back legs back
    d.ellipse((164, 114, 182, 128), fill=W); d.ellipse((8, 122, 26, 136), fill=W)
    d.ellipse((120, 84, 152, 108), fill=W)                      # chest
    d.ellipse((128, 22, 196, 82), fill=O)                       # head
    d.polygon([(134, 40), (138, 2), (160, 28)], fill=O); d.polygon([(170, 26), (192, 2), (196, 44)], fill=O)
    d.polygon([(141, 26), (141, 14), (150, 24)], fill=P); d.polygon([(181, 24), (189, 14), (189, 30)], fill=P)
    d.ellipse((150, 56, 184, 80), fill=W)
    d.rectangle((148, 42, 157, 53), fill=E); d.rectangle((174, 42, 183, 53), fill=E)
    d.rectangle((163, 56, 170, 62), fill=P)

def sleep(d):
    d.ellipse((20, 50, 160, 118), fill=O)                       # curled body
    d.line([(30, 104), (60, 116), (120, 116)], fill=O, width=14, joint="curve")          # tail around the front
    d.ellipse((96, 40, 166, 104), fill=O)                       # head resting
    d.polygon([(100, 62), (106, 22), (128, 48)], fill=O); d.polygon([(138, 44), (160, 20), (164, 64)], fill=O)
    d.polygon([(107, 46), (107, 34), (116, 42)], fill=P); d.polygon([(150, 38), (157, 30), (157, 46)], fill=P)
    d.ellipse((118, 78, 152, 100), fill=W)
    d.rectangle((112, 72, 129, 75), fill=E); d.rectangle((140, 72, 157, 75), fill=E)    # closed eyes
    d.rectangle((132, 80, 139, 86), fill=P)

art = {"sit": make(20, 24, sit), "jump": make(25, 18, jump), "sleep": make(23, 17, sleep)}
json.dump(art, open(sys.argv[1], "w"), indent=1)
for k, v in art.items():
    print(k); print("\n".join(v))

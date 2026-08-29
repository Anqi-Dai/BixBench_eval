# Render a static preview of the interactive run audit for the README.
#
# GitHub READMEs cannot run scripts, so the live page cannot embed there.
# This composes a faithful still of the page — the run grid with one tooltip
# card open and a cursor on the cell it describes — so the README preview
# looks like what the click delivers. Cell states come from
# results/model_data.csv; the agent-attribution set mirrors the rules in
# R/figures.R and env/REVIEW_REPORT.md.
#
# Run:  uv run --with pillow python py/make_interactive_preview.py
# Output: results/figures/fig4_interactive_preview.png

import csv
from PIL import Image, ImageDraw, ImageFont

W, H = 1500, 1210
SURFACE = "#faf9f6"
INK = "#201f1c"
INK2 = "#6b6960"
MUTED = "#898781"
LINE = "#e6e4dc"
GOOD = "#0f8f0f"
BAD = "#c93a3a"
NONE = "#8f8d85"
CHIPBG = "#f1efe9"

FONTS = "/System/Library/Fonts/Supplemental/"
f_title = ImageFont.truetype(FONTS + "Arial Bold.ttf", 44)
f_lede = ImageFont.truetype(FONTS + "Arial.ttf", 28)
f_cap = ImageFont.truetype(FONTS + "Arial Bold.ttf", 24)
f_lab = ImageFont.truetype(FONTS + "Arial.ttf", 26)
f_tip = ImageFont.truetype(FONTS + "Arial.ttf", 24)
f_tipb = ImageFont.truetype(FONTS + "Arial Bold.ttf", 24)
f_mono = ImageFont.truetype(FONTS + "Courier New.ttf", 24)

# Runs the review report attributes to the agent (hatched on the live page).
AGENT = {("bix-26-q5", r) for r in (1, 6, 7, 8, 9)} | {("bix-26-q4", 0),
                                                       ("bix-26-q4", 5),
                                                       ("bix-26-q4", 9)}

state = {}
for r in csv.DictReader(open("results/model_data.csv")):
    q, rep = r["question"], int(r["replica"])
    state[(q, rep)] = ("correct" if r["correct_gpt5"] == "TRUE"
                       else "incorrect" if r["responded"] == "TRUE"
                       else "noanswer")

img = Image.new("RGB", (W, H), SURFACE)
d = ImageDraw.Draw(img)
M = 60

d.text((M, 40), "The 140-Run Audit", font=f_title, fill=INK)
d.text((M, 104), "Hover or tap any run for its verified cause, classification, "
                 "and confidence.", font=f_lede, fill=INK2)

# legend chips
x = M
for color, label in [(GOOD, "correct"), (BAD, "incorrect"),
                     (NONE, "no answer"), (None, "hatched = agent's own")]:
    w = int(d.textlength(label, font=f_lab)) + (66 if color else 30)
    d.rounded_rectangle([x, 158, x + w, 200], 21, fill=CHIPBG, outline=LINE)
    if color:
        d.rounded_rectangle([x + 18, 168, x + 42, 190], 5, fill=color)
        d.text((x + 52, 168), label, font=f_lab, fill=INK2)
    else:
        d.text((x + 15, 168), label, font=f_lab, fill=INK2)
    x += w + 14

CELL, GAP = 40, 7


def draw_cell(x, y, st, agent):
    fill = {"correct": GOOD, "incorrect": BAD, "noanswer": NONE}[st]
    d.rounded_rectangle([x, y, x + CELL, y + CELL], 8, fill=fill)
    if agent:
        # white diagonal hatch, clipped to the cell by drawing on a patch
        patch = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
        pd = ImageDraw.Draw(patch)
        for k in range(-CELL, CELL * 2, 12):
            pd.line([(k, CELL), (k + CELL, 0)], fill=(255, 255, 255, 220),
                    width=4)
        mask = Image.new("L", (CELL, CELL), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, CELL - 1, CELL - 1], 8,
                                               fill=255)
        img.paste(patch, (int(x), int(y)), Image.composite(patch.split()[3],
                  Image.new("L", (CELL, CELL), 0), mask))


# the grid, grouped by capsule
CAPS = [("bix-8", ["bix-8-q1", "bix-8-q2", "bix-8-q3", "bix-8-q5",
                   "bix-8-q6", "bix-8-q7"]),
        ("bix-49", [f"bix-49-q{i}" for i in range(1, 6)]),
        ("bix-26", ["bix-26-q3", "bix-26-q4", "bix-26-q5"])]
y = 250
row_y = {}
for cap, qs in CAPS:
    d.text((M, y), cap.upper(), font=f_cap, fill=INK2)
    d.line([(M, y + 40), (W - M, y + 40)], fill=LINE, width=2)
    y += 58
    for q in qs:
        d.text((M + 150 - d.textlength(q, font=f_lab), y + 6), q,
               font=f_lab, fill=INK)
        for rep in range(10):
            draw_cell(M + 180 + rep * (CELL + GAP), y,
                      state[(q, rep)], (q, rep) in AGENT)
        row_y[q] = y
        y += CELL + 12
    y += 26

# tooltip card for bix-26-q5 replicate 9 (the invented-metric run), floating
# above its row with the cursor on the cell
tx, ty, tw, th = 640, row_y["bix-26-q5"] - 332, 660, 312
d.rounded_rectangle([tx + 6, ty + 10, tx + tw + 6, ty + th + 10], 16,
                    fill="#d9d7cf")  # soft shadow
d.rounded_rectangle([tx, ty, tx + tw, ty + th], 16, fill="#ffffff",
                    outline=LINE, width=2)
d.text((tx + 26, ty + 22), "bix-26-q5 · replicate 9", font=f_mono, fill=INK2)
bx = tx + 26
for text, fill, fg in [("incorrect", BAD, "#ffffff"),
                       ("the agent's own", None, INK2),
                       ("Documented", None, INK2)]:
    w = int(d.textlength(text, font=f_tipb)) + 30
    d.rounded_rectangle([bx, ty + 62, bx + w, ty + 98], 18,
                        fill=fill, outline=None if fill else LINE)
    d.text((bx + 15, ty + 68), text, font=f_tipb, fill=fg)
    bx += w + 12
d.text((tx + 26, ty + 116), "Agent error", font=f_tipb, fill=INK)
cause = ("Hand-rolled ORA with an invented pathway-level \"fold change\" "
         "to satisfy the wording.")
cy = ty + 152
words, cur = cause.split(), ""
for wd in words:
    t = (cur + " " + wd).strip()
    if d.textlength(t, font=f_tip) <= tw - 52:
        cur = t
    else:
        d.text((tx + 26, cy), cur, font=f_tip, fill=INK2)
        cy += 34
        cur = wd
d.text((tx + 26, cy), cur, font=f_tip, fill=INK2)
d.rounded_rectangle([tx + 26, ty + th - 76, tx + tw - 26, ty + th - 18], 10,
                    fill=CHIPBG)
d.text((tx + 40, ty + th - 66), "agent 2    key 3", font=f_mono, fill=INK)

# cursor arrow on the described cell (bix-26-q5, replicate 9)
cx = M + 180 + 9 * (CELL + GAP) + 14
cyy = row_y["bix-26-q5"] + 14
d.polygon([(cx, cyy), (cx, cyy + 34), (cx + 9, cyy + 26), (cx + 15, cyy + 40),
           (cx + 22, cyy + 36), (cx + 16, cyy + 23), (cx + 26, cyy + 21)],
          fill="#1a1a1a", outline="#ffffff")

img.save("results/figures/fig4_interactive_preview.png")
print("wrote results/figures/fig4_interactive_preview.png")

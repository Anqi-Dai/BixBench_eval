# Build the LinkedIn carousel PDF from the four square figures.
#
# LinkedIn renders a multi-page PDF as swipeable pages. This script composes
# six square pages — a cover, the four figures each with a one-line takeaway
# strip, and a closing page with the links — and writes a single PDF.
#
# Run:  uv run --with pillow python py/make_carousel.py
# Output: results/figures/linkedin_carousel.pdf

from PIL import Image, ImageDraw, ImageFont

# Page geometry: 2250 px square at 300 dpi = 7.5 inches, matching the
# figures' own resolution so they paste without resampling artifacts.
PAGE = 2250

# The figures' palette, so the carousel reads as the same document.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
CRITICAL = "#d03b3b"
GOOD = "#0ca30c"

FONTS = "/System/Library/Fonts/Supplemental/"


def font(name, size):
    # Arial throughout: closest system match to the figures' Helvetica-like
    # sans, available on every macOS build.
    return ImageFont.truetype(FONTS + name, size)


F_EYEBROW = font("Arial Bold.ttf", 54)
F_TITLE = font("Arial Black.ttf", 150)
F_SUB = font("Arial.ttf", 84)
F_BODY = font("Arial.ttf", 56)
F_STRIP = font("Arial.ttf", 58)
F_STRIP_B = font("Arial Bold.ttf", 58)
F_FOOT = font("Arial.ttf", 48)


def new_page():
    return Image.new("RGB", (PAGE, PAGE), SURFACE)


def wrapped(draw, text, fnt, max_w):
    # Greedy word wrap against the rendered pixel width.
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def draw_wrapped(draw, xy, text, fnt, fill, max_w, leading=1.35):
    x, y = xy
    for line in wrapped(draw, text, fnt, max_w):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * leading)
    return y


pages = []

# ---- page 1: cover ---------------------------------------------------------
# The hook states the thesis question, not the verdict; the verdict arrives
# with its evidence on the figure pages.
p = new_page()
d = ImageDraw.Draw(p)
M = 170
d.text((M, 300), "AN AUDIT OF BIXBENCH", font=F_EYEBROW, fill=MUTED)
y = 420
for line in ["What the", "score hides"]:
    d.text((M, y), line, font=F_TITLE, fill=INK)
    y += 185
y += 60
y = draw_wrapped(
    d, (M, y),
    "A bioinformatics-agent benchmark scores each question with a single "
    "pooled number. I replicated the runs, replicated the grading, and "
    "re-derived every answer key to see what that number leaves out.",
    F_SUB, INK2, PAGE - 2 * M)
y += 90
for stat, label in [("140", "agent runs, 10 per question"),
                    ("3,900", "grading verdicts, 3 graders × 10 rounds"),
                    ("14", "answer keys re-derived from raw data")]:
    d.text((M, y), stat, font=F_STRIP_B, fill=CRITICAL)
    d.text((M + 320, y), label, font=F_STRIP, fill=INK2)
    y += 105
d.text((M, PAGE - 230), "swipe →", font=F_SUB, fill=MUTED)
pages.append(p)

# ---- pages 2-5: the figures, each with a takeaway strip --------------------
# Figures scale to 88% of the page, leaving a bottom strip for the one
# standalone line the lean in-figure subtitles no longer carry.
TAKEAWAYS = [
    ("fig1_grader_flips.png",
     "Two current-generation graders agree on all 130 answers. The shipped "
     "previous-generation grader contradicts itself on 14.6% of them."),
    ("fig2_three_states.png",
     "10 of 140 runs never answered - and 9 of those died following the "
     "harness's own package-install instruction."),
    ("fig3_question_rates.png",
     "Per-question success is near-certain or near-impossible, with almost "
     "nothing between: the outcome belongs to the question."),
    ("fig4_failure_causes.png",
     "Re-deriving every key from the raw data: most incorrect answers trace "
     "to the answer key or the question's wording, each cause verified."),
]
for fname, take in TAKEAWAYS:
    p = new_page()
    d = ImageDraw.Draw(p)
    fig = Image.open("results/figures/" + fname)
    # 82% leaves room for a two-line takeaway strip inside the page
    side = int(PAGE * 0.82)
    fig = fig.resize((side, side), Image.LANCZOS)
    p.paste(fig, ((PAGE - side) // 2, 30))
    d.line([(170, side + 90), (PAGE - 170, side + 90)], fill="#e1e0d9", width=4)
    draw_wrapped(d, (170, side + 135), take, F_STRIP, INK2, PAGE - 340)
    pages.append(p)

# ---- page 6: closing -------------------------------------------------------
p = new_page()
d = ImageDraw.Draw(p)
d.text((M, 320), "READ THE FULL AUDIT", font=F_EYEBROW, fill=MUTED)
y = 450
d.text((M, y), "Every claim is", font=F_TITLE, fill=INK)
y += 185
d.text((M, y), "recomputable", font=F_TITLE, fill=GOOD)
y += 260
y = draw_wrapped(
    d, (M, y),
    "The writeup, the code, the grading data, and the case-by-case failure "
    "attribution are public - every recomputation is a committed script.",
    F_SUB, INK2, PAGE - 2 * M)
y += 110
for label, url in [
        ("Writeup + code", "github.com/Anqi-Dai/BixBench_eval"),
        ("Interactive run audit", "anqi-dai.github.io/BixBench_eval/results/figures/fig4_interactive.html"),
        ("Data DOI", "10.5281/zenodo.22151974")]:
    d.text((M, y), label, font=F_STRIP_B, fill=INK)
    d.text((M, y + 78), url, font=F_BODY, fill=CRITICAL)
    y += 230
pages.append(p)

pages[0].save("results/figures/linkedin_carousel.pdf", save_all=True,
              append_images=pages[1:], resolution=300)
print(f"wrote results/figures/linkedin_carousel.pdf ({len(pages)} pages)")

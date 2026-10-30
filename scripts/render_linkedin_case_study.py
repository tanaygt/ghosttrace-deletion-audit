from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
W, H = 1800, 1125
NAVY = (18, 34, 60)
INK = (31, 49, 76)
MUTED = (91, 108, 130)
TEAL = (0, 157, 169)
TEAL_PALE = (231, 248, 248)
BLUE = (62, 105, 173)
BLUE_PALE = (236, 243, 255)
ORANGE = (222, 113, 40)
ORANGE_PALE = (255, 243, 233)
RED = (193, 70, 65)
RED_PALE = (253, 237, 236)
GREEN = (43, 143, 95)
GREEN_PALE = (233, 248, 239)
BG = (247, 249, 252)
WHITE = (255, 255, 255)
LINE = (218, 226, 235)

try:
    body = ImageFont.truetype("segoeui.ttf", 24)
    small = ImageFont.truetype("segoeui.ttf", 19)
    tiny = ImageFont.truetype("segoeui.ttf", 16)
    h2 = ImageFont.truetype("segoeuib.ttf", 31)
    h1 = ImageFont.truetype("segoeuib.ttf", 62)
    metric = ImageFont.truetype("segoeuib.ttf", 48)
except OSError:
    body = small = tiny = h2 = h1 = metric = ImageFont.load_default()


def text(d, xy, value, font=body, fill=INK, anchor=None):
    d.text(xy, value, font=font, fill=fill, anchor=anchor)


def wrap(d, value, width, font):
    lines, line = [], ""
    for word in value.split():
        candidate = f"{line} {word}".strip()
        if d.textlength(candidate, font=font) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def paragraph(d, x, y, value, width, font=body, fill=MUTED, gap=9):
    for line in wrap(d, value, width, font):
        text(d, (x, y), line, font, fill)
        y += font.size + gap
    return y


def card(d, xy, fill=WHITE, outline=LINE, radius=20, width=2):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def header(d, page, kicker, title, subtitle):
    d.rounded_rectangle((44, 34, W - 44, 126), radius=22, fill=NAVY)
    d.rounded_rectangle((78, 61, 90, 99), radius=6, fill=TEAL)
    text(d, (116, 56), "GhostTrace", h2, WHITE)
    text(d, (116, 94), kicker.upper(), tiny, (181, 204, 226))
    text(d, (W - 78, 80), page, body, (181, 204, 226), "ra")
    text(d, (74, 178), title, h1, NAVY)
    paragraph(d, 78, 258, subtitle, 1500, body, MUTED)


def footer(d):
    d.line((74, 1072, W - 74, 1072), fill=LINE, width=2)
    text(d, (74, 1090), "GhostTrace  •  evidence-first deletion auditing  •  CLI-first project", tiny, MUTED)
    text(d, (W - 74, 1090), "github.com/tanaygt/ghosttrace-deletion-audit", tiny, TEAL, "ra")


def number(d, x, y, value, label, color):
    text(d, (x, y), value, metric, color)
    text(d, (x, y + 58), label, tiny, (181, 204, 226))


def case_study():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "01 / 02", "The problem", "Deletion is not a button.", "In a distributed system, “Complete” is a workflow status. The real question is whether the data is gone—and cannot come back.")

    card(d, (76, 390, 830, 855), NAVY, NAVY)
    text(d, (122, 440), "THE CLAIM", tiny, (132, 229, 231))
    text(d, (122, 488), "“Account deleted”", h2, WHITE)
    text(d, (122, 548), "is not the same as", body, (181, 204, 226))
    text(d, (122, 596), "“data proven gone”", h2, (255, 201, 170))
    d.line((122, 676, 760, 676), fill=(61, 83, 112), width=2)
    text(d, (122, 718), "The hidden surface", tiny, (181, 204, 226))
    paragraph(d, 122, 758, "replicas  •  search  •  analytics  •  support files  •  exports  •  logs  •  backups  •  sync jobs", 600, small, WHITE, 8)

    text(d, (910, 400), "What GhostTrace investigates", h2, NAVY)
    items = [("01", "Identity history", "current and historical emails, phones, and IDs", BLUE_PALE, BLUE), ("02", "Evidence surface", "structured files, logs, SQL, PDFs, and images", TEAL_PALE, TEAL), ("03", "Recreation risk", "sync, import, and restore paths that can bring data back", ORANGE_PALE, ORANGE), ("04", "Policy outcome", "delete, redact, anonymize, retain, or block", GREEN_PALE, GREEN)]
    for i, (n, name, detail, fill, accent) in enumerate(items):
        y = 480 + i * 105
        card(d, (910, y, 1690, y + 78), fill, fill, 16, 1)
        text(d, (946, y + 18), n, h2, accent)
        text(d, (1020, y + 13), name, small, NAVY)
        text(d, (1020, y + 43), detail, tiny, MUTED)
    footer(d)
    return im


def approach():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    header(d, "02 / 02", "The approach", "Evidence in. Proof out.", "GhostTrace turns messy records into a deterministic decision, an ordered remediation plan, and checks that can prove the result.")

    steps = [(110, "Resolve", "identity graph", BLUE), (420, "Inspect", "multimodal evidence", TEAL), (730, "Rebuild", "audit_at timeline", BLUE), (1040, "Compile", "deletion rules", TEAL), (1350, "Verify", "ordered proof", ORANGE)]
    for i, (x, name, detail, accent) in enumerate(steps):
        d.ellipse((x, 410, x + 70, 480), fill=accent)
        text(d, (x + 35, 445), str(i + 1), h2, WHITE, "mm")
        text(d, (x, 520), name, h2, NAVY)
        text(d, (x, 565), detail, small, MUTED)
        if i < len(steps) - 1:
            d.line((x + 88, 445, x + 285, 445), fill=LINE, width=4)
            d.polygon([(x + 305, 445), (x + 282, 432), (x + 282, 458)], fill=LINE)

    card(d, (110, 660, 900, 930), WHITE, LINE, 20, 2)
    text(d, (150, 700), "Output contract", h2, NAVY)
    rows = [("COMPLETE", "verification evidence only", GREEN), ("INCOMPLETE", "findings + remediation + checks", RED), ("NOT_APPLICABLE", "no deletion authorization", BLUE)]
    for i, (name, desc, color) in enumerate(rows):
        y = 770 + i * 48
        d.ellipse((152, y + 5, 168, y + 21), fill=color)
        text(d, (190, y), name, small, NAVY)
        text(d, (460, y), desc, tiny, MUTED)

    card(d, (970, 660, 1690, 930), NAVY, NAVY, 20, 1)
    text(d, (1010, 700), "Measured public sample", h2, WHITE)
    number(d, 1010, 770, "518", "cases generated", (132, 229, 231))
    number(d, 1220, 770, "96.88%", "status accuracy", (255, 190, 150))
    number(d, 1490, 770, "73.54%", "step F1", (185, 205, 255))
    footer(d)
    return im


OUT.mkdir(parents=True, exist_ok=True)
for index, image in enumerate([case_study(), approach()], 1):
    path = OUT / f"linkedin-case-study-{index:02d}.png"
    image.save(path, "PNG", optimize=True)
    print(path)

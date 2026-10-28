from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
W, H = 1800, 1125
NAVY = (16, 30, 54)
INK = (25, 42, 68)
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
BG = (245, 248, 251)
WHITE = (255, 255, 255)
LINE = (218, 226, 235)

try:
    regular = ImageFont.truetype("segoeui.ttf", 24)
    small = ImageFont.truetype("segoeui.ttf", 19)
    tiny = ImageFont.truetype("segoeui.ttf", 16)
    bold = ImageFont.truetype("segoeuib.ttf", 30)
    title = ImageFont.truetype("segoeuib.ttf", 58)
    metric = ImageFont.truetype("segoeuib.ttf", 42)
except OSError:
    regular = small = tiny = bold = title = metric = ImageFont.load_default()


def txt(draw, xy, value, font=regular, fill=INK, anchor=None):
    draw.text(xy, value, font=font, fill=fill, anchor=anchor)


def wrap(draw, value, width, font):
    lines, line = [], ""
    for word in value.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def para(draw, x, y, value, width, font=regular, fill=MUTED, gap=8):
    for line in wrap(draw, value, width, font):
        txt(draw, (x, y), line, font, fill)
        y += font.size + gap
    return y


def card(draw, xy, fill=WHITE, outline=LINE, radius=18, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def topbar(draw, page, label):
    draw.rounded_rectangle((44, 34, W - 44, 122), radius=20, fill=NAVY)
    draw.rounded_rectangle((76, 60, 88, 96), radius=6, fill=TEAL)
    txt(draw, (112, 54), "GhostTrace", bold, WHITE)
    txt(draw, (112, 91), label.upper(), tiny, (178, 201, 224))
    txt(draw, (W - 78, 78), page, regular, (178, 201, 224), "ra")


def footer(draw):
    draw.line((72, 1074, W - 72, 1074), fill=LINE, width=2)
    txt(draw, (72, 1090), "Evidence-first deletion auditing  •  Python  •  privacy engineering", tiny, MUTED)
    txt(draw, (W - 72, 1090), "github.com/tanaygt/ghosttrace-deletion-audit", tiny, TEAL, "ra")


def badge(draw, x, y, label, fill, color, width=None):
    width = width or int(draw.textlength(label, font=tiny)) + 28
    card(draw, (x, y, x + width, y + 34), fill, fill, 17, 1)
    txt(draw, (x + width / 2, y + 17), label, tiny, color, "mm")


def dashboard():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    topbar(d, "01 / 02", "A clean product view")
    txt(d, (74, 170), "GhostTrace Audit Console", title, NAVY)
    para(d, 76, 246, "A deletion request becomes a traceable decision—not a checkbox.", 1160, regular, MUTED)

    # Main app frame
    card(d, (72, 330, 1728, 1018), WHITE, LINE, 22, 2)
    d.rectangle((72, 330, 360, 1018), fill=(249, 251, 253))
    d.line((360, 330, 360, 1018), fill=LINE, width=2)
    txt(d, (108, 378), "AUDIT WORKSPACE", tiny, MUTED)
    for y, label, active in [(432, "Overview", True), (486, "Evidence map", False), (540, "Remediation", False), (594, "Verification", False)]:
        if active:
            card(d, (96, y - 14, 330, y + 28), TEAL_PALE, TEAL_PALE, 12, 1)
        d.ellipse((116, y - 1, 130, y + 13), fill=TEAL if active else LINE)
        txt(d, (150, y - 7), label, small, NAVY if active else MUTED)
    txt(d, (108, 700), "REQUEST", tiny, MUTED)
    txt(d, (108, 736), "del-2026-00418", bold, NAVY)
    txt(d, (108, 776), "audit_at", tiny, MUTED)
    txt(d, (108, 806), "2026-10-26 14:32 UTC", small, INK)
    badge(d, 108, 870, "INCOMPLETE", RED_PALE, RED, 142)
    txt(d, (108, 928), "3 findings require action", small, RED)

    # Main header row
    txt(d, (410, 378), "Deletion audit", bold, NAVY)
    badge(d, 1450, 360, "INCOMPLETE", RED_PALE, RED, 142)
    txt(d, (410, 438), "Identity resolution", tiny, MUTED)
    txt(d, (410, 468), "customer_4821  →  6 historical identifiers", small, INK)
    txt(d, (410, 540), "Coverage", tiny, MUTED)
    d.rounded_rectangle((410, 570, 1300, 592), radius=11, fill=(234, 239, 245))
    d.rounded_rectangle((410, 570, 1160, 592), radius=11, fill=TEAL)
    txt(d, (1322, 567), "84% checked", small, TEAL)

    # Evidence table
    txt(d, (410, 650), "Evidence found", bold, NAVY)
    rows = [
        ("Primary account", "deleted", "verified", GREEN_PALE, GREEN),
        ("Search index", "email still indexed", "action needed", RED_PALE, RED),
        ("Analytics export", "historical identifier", "redact", ORANGE_PALE, ORANGE),
        ("Backup restore job", "can recreate record", "block + recheck", BLUE_PALE, BLUE),
    ]
    for i, (source, finding, action, fill, color) in enumerate(rows):
        y = 700 + i * 57
        if i % 2 == 0:
            d.rectangle((410, y - 12, 1662, y + 40), fill=(251, 252, 254))
        txt(d, (430, y), source, small, NAVY)
        txt(d, (760, y), finding, small, MUTED)
        badge(d, 1390, y - 8, action, fill, color)
    footer(d)
    return im


def systems():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    topbar(d, "02 / 02", "How it works")
    txt(d, (74, 170), "From request to defensible proof", title, NAVY)
    para(d, 76, 246, "GhostTrace joins identity history, multimodal evidence, time, policy, and recreation risk into one ordered audit.", 1450, regular, MUTED)

    # Workflow ribbon
    steps = [(110, "01", "Resolve", "current + historical IDs", BLUE), (430, "02", "Inspect", "CSV • JSON • SQL • PDF • image", TEAL), (750, "03", "Rebuild", "state at audit_at", BLUE), (1070, "04", "Decide", "delete • redact • retain", TEAL), (1390, "05", "Prove", "findings + checks", BLUE)]
    for i, (x, number, name, detail, accent) in enumerate(steps):
        card(d, (x, 370, x + 290, 530), WHITE, LINE, 18, 2)
        txt(d, (x + 28, 402), number, bold, accent)
        txt(d, (x + 28, 452), name, bold, NAVY)
        para(d, x + 28, 490, detail, 230, small, MUTED, 4)
        if i < len(steps) - 1:
            d.line((x + 298, 450, x + 312, 450), fill=LINE, width=4)
            d.polygon([(x + 322, 450), (x + 308, 441), (x + 308, 459)], fill=LINE)

    # Evidence-to-decision diagram
    card(d, (110, 590, 1160, 985), WHITE, LINE, 20, 2)
    txt(d, (150, 630), "Evidence surface", bold, NAVY)
    sources = [("Identity graph", "email • phone • legacy ID", BLUE_PALE, BLUE), ("System copies", "replicas • search • exports", TEAL_PALE, TEAL), ("Recovery paths", "sync • import • backup restore", ORANGE_PALE, ORANGE)]
    for i, (name, detail, fill, accent) in enumerate(sources):
        y = 710 + i * 82
        card(d, (150, y, 680, y + 58), fill, fill, 14, 1)
        d.ellipse((174, y + 18, 194, y + 38), fill=accent)
        txt(d, (220, y + 12), name, small, NAVY)
        txt(d, (220, y + 36), detail, tiny, MUTED)
    txt(d, (760, 776), "policy compiler", bold, TEAL, "mm")
    d.line((690, 810, 830, 810), fill=TEAL, width=5)
    d.polygon([(850, 810), (832, 799), (832, 821)], fill=TEAL)
    card(d, (870, 710, 1115, 910), NAVY, NAVY, 18, 1)
    txt(d, (900, 742), "Decision", bold, WHITE)
    txt(d, (900, 800), "COMPLETE", small, (132, 229, 231))
    txt(d, (900, 835), "INCOMPLETE", small, (255, 190, 150))
    txt(d, (900, 870), "NOT_APPLICABLE", small, (190, 205, 225))

    card(d, (1215, 590, 1690, 985), NAVY, NAVY, 20, 1)
    txt(d, (1260, 630), "What ships", bold, WHITE)
    deliverables = ["ordered findings", "remediation steps", "verification checks", "retention-safe records", "validator + tests", "reproducible CLI"]
    for i, label in enumerate(deliverables):
        y = 704 + i * 42
        d.ellipse((1262, y + 4, 1278, y + 20), fill=TEAL)
        txt(d, (1300, y), label, small, (224, 236, 248))
    footer(d)
    return im


OUT.mkdir(parents=True, exist_ok=True)
for index, image in enumerate([dashboard(), systems()], 1):
    path = OUT / f"linkedin-ui-{index:02d}.png"
    image.save(path, "PNG", optimize=True)
    print(path)

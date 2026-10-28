from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
W, H = 1600, 900
NAVY = (19, 36, 63)
INK = (29, 45, 70)
MUTED = (91, 108, 130)
TEAL = (0, 151, 164)
TEAL_LIGHT = (229, 247, 247)
BLUE = (62, 105, 173)
BLUE_LIGHT = (235, 242, 253)
ORANGE = (222, 113, 40)
ORANGE_LIGHT = (255, 241, 230)
RED = (190, 70, 64)
RED_LIGHT = (253, 235, 234)
BG = (248, 250, 252)
WHITE = (255, 255, 255)
LINE = (218, 226, 235)

try:
    body = ImageFont.truetype("segoeui.ttf", 24)
    small = ImageFont.truetype("segoeui.ttf", 18)
    h2 = ImageFont.truetype("segoeuib.ttf", 34)
    h1 = ImageFont.truetype("segoeuib.ttf", 64)
    metric = ImageFont.truetype("segoeuib.ttf", 48)
except OSError:
    body = small = h2 = h1 = metric = ImageFont.load_default()


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


def text(draw, xy, value, font=body, fill=INK, anchor=None):
    draw.text(xy, value, font=font, fill=fill, anchor=anchor)


def paragraph(draw, x, y, value, width, font=body, fill=MUTED, gap=10):
    for line in wrap(draw, value, width, font):
        text(draw, (x, y), line, font, fill)
        y += font.size + gap
    return y


def box(draw, xy, fill=WHITE, outline=LINE, radius=18, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def header(draw, page, section, title, subtitle):
    draw.rounded_rectangle((42, 34, W - 42, 155), radius=24, fill=NAVY)
    draw.rounded_rectangle((76, 66, 90, 124), radius=7, fill=TEAL)
    text(draw, (120, 57), "GhostTrace", h2, WHITE)
    text(draw, (120, 104), section.upper(), small, (181, 204, 226))
    text(draw, (W - 80, 95), f"{page}/4", body, (181, 204, 226), "ra")
    text(draw, (72, 213), title, h1, NAVY)
    paragraph(draw, 76, 300, subtitle, 1180, body, MUTED)


def footer(draw):
    draw.line((72, 826, W - 72, 826), fill=LINE, width=2)
    text(draw, (72, 850), "Python  •  privacy engineering  •  distributed systems", small, MUTED)
    text(draw, (W - 72, 850), "github.com/tanaygt/ghosttrace-deletion-audit", small, TEAL, "ra")


def arrow(draw, x1, y1, x2, y2, color=LINE):
    draw.line((x1, y1, x2, y2), fill=color, width=4)
    draw.polygon([(x2, y2), (x2 - 14, y2 - 8), (x2 - 14, y2 + 8)], fill=color)


def cover():
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    header(draw, 1, "Project introduction", "Can you prove deleted data is gone?", "GhostTrace is an evidence-first deletion audit agent for distributed customer data.")
    box(draw, (76, 405, 820, 690), WHITE, LINE)
    text(draw, (116, 445), "The real-world problem", h2, NAVY)
    paragraph(draw, 116, 510, "A dashboard can say “Complete” while copies still exist in replicas, search, analytics, support, exports, logs, backups, or active sync jobs.", 610, body)
    pill = (116, 620, 370, 664)
    box(draw, pill, RED_LIGHT, RED, 22, 1)
    text(draw, (301, 642), "workflow status ≠ proof", small, RED, "mm")
    box(draw, (900, 405, 1524, 690), TEAL_LIGHT, (183, 229, 230))
    text(draw, (940, 445), "What GhostTrace does", h2, NAVY)
    text(draw, (940, 520), "request", body, BLUE, "lm")
    arrow(draw, 1045, 520, 1140, 520, TEAL)
    text(draw, (1170, 520), "evidence", body, TEAL, "lm")
    arrow(draw, 1280, 520, 1375, 520, TEAL)
    text(draw, (1405, 520), "proof", body, ORANGE, "lm")
    paragraph(draw, 940, 590, "It connects identity history, time, evidence, retention rules, and recreation risks into one ordered audit plan.", 505, body)
    footer(draw)
    return image


def problem():
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    header(draw, 2, "Why it matters", "Deletion is a system-wide problem", "One customer record can appear in many systems—and a sync or restore process can bring it back.")
    box(draw, (72, 402, 490, 724), NAVY, NAVY)
    text(draw, (112, 445), "DELETE", h2, (132, 229, 231))
    text(draw, (112, 515), "the account", h2, WHITE)
    text(draw, (112, 590), "but first prove", body, (181, 204, 226))
    text(draw, (112, 630), "every copy", h2, WHITE)
    text(draw, (112, 682), "has the right treatment", body, (181, 204, 226))
    systems = [
        (560, 402, "Database replicas", "old rows can survive", RED_LIGHT, RED),
        (1040, 402, "Search + analytics", "indexes can keep PII", ORANGE_LIGHT, ORANGE),
        (560, 555, "Support + exports", "attachments and files", BLUE_LIGHT, BLUE),
        (1040, 555, "Backups + sync", "data can return", TEAL_LIGHT, TEAL),
    ]
    for x, y, name, detail, fill, accent in systems:
        box(draw, (x, y, x + 430, y + 120), fill, fill)
        draw.ellipse((x + 24, y + 31, x + 64, y + 71), fill=accent)
        text(draw, (x + 88, y + 28), name, h2, NAVY)
        text(draw, (x + 88, y + 76), detail, small, MUTED)
    box(draw, (560, 708, 910, 762), WHITE, LINE, 27, 1)
    text(draw, (735, 735), "Ghost data", body, RED, "mm")
    arrow(draw, 920, 735, 1010, 735, RED)
    text(draw, (1040, 735), "financial + trust risk", body, RED)
    footer(draw)
    return image


def workflow():
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    header(draw, 3, "The approach", "From request to evidence-backed proof", "The engine is deterministic by default, with optional AI enrichment isolated from policy decisions.")
    steps = [
        (72, "01", "Resolve identity", "Match current and historical identifiers exactly."),
        (372, "02", "Read evidence", "Parse CSV, JSON, SQL, logs, PDFs, and images."),
        (672, "03", "Rebuild time", "Use the state at the request’s audit_at cutoff."),
        (972, "04", "Apply rules", "Delete, redact, anonymize, retain, disable, or block."),
        (1272, "05", "Generate proof", "Return ordered findings, actions, and checks."),
    ]
    for i, (x, number, name, detail) in enumerate(steps):
        fill = TEAL_LIGHT if i % 2 else BLUE_LIGHT
        accent = TEAL if i % 2 else BLUE
        box(draw, (x, 438, x + 250, 670), fill, fill)
        text(draw, (x + 28, 468), number, h2, accent)
        text(draw, (x + 28, 522), name, h2, NAVY)
        paragraph(draw, x + 28, 580, detail, 195, small, MUTED, 7)
        if i < len(steps) - 1:
            arrow(draw, x + 260, 544, x + 292, 544, LINE)
    box(draw, (72, 712, 1522, 780), WHITE, LINE, 20, 1)
    text(draw, (100, 746), "Design principle", small, TEAL)
    text(draw, (270, 746), "A successful workflow event is a claim. A direct, time-aware readback is evidence.", body, NAVY)
    footer(draw)
    return image


def results():
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    header(draw, 4, "What was delivered", "A runnable, explainable audit agent", "GhostTrace turns messy evidence into a structured decision and a safe next-step plan.")
    box(draw, (72, 400, 760, 760), NAVY, NAVY)
    text(draw, (112, 440), "OUTPUT STATES", h2, (132, 229, 231))
    for y, label, desc in [(515, "COMPLETE", "verification evidence only"), (590, "INCOMPLETE", "findings + remediation + checks"), (665, "NOT_APPLICABLE", "no deletion authorization")]:
        text(draw, (112, y), label, h2, WHITE)
        text(draw, (112, y + 39), desc, small, (181, 204, 226))
    box(draw, (840, 400, 1524, 760), WHITE, LINE)
    text(draw, (880, 440), "MEASURED PUBLIC SAMPLE", h2, NAVY)
    metrics = [(880, "518", "cases generated", TEAL), (1090, "96.88%", "status accuracy", ORANGE), (1340, "73.54%", "step F1", BLUE)]
    for x, value, label, color in metrics:
        text(draw, (x, 530), value, metric, color)
        text(draw, (x, 595), label, small, MUTED)
    text(draw, (880, 665), "Also included:", body, NAVY)
    text(draw, (880, 705), "validator • regression tests • evaluation report", small, MUTED)
    text(draw, (880, 735), "usage report • README • reproducible CLI workflow", small, MUTED)
    footer(draw)
    return image


OUT.mkdir(parents=True, exist_ok=True)
for index, image in enumerate([cover(), problem(), workflow(), results()], 1):
    path = OUT / f"linkedin-carousel-{index:02d}.png"
    image.save(path, "PNG", optimize=True)
    print(path)

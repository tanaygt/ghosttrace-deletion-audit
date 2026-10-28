from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "linkedin-infographic.png"
W, H = 1600, 1000
BG = (247, 250, 252)
NAVY = (18, 35, 62)
MUTED = (82, 101, 126)
TEAL = (0, 153, 166)
TEAL_SOFT = (224, 247, 247)
BLUE_SOFT = (232, 240, 252)
ORANGE = (225, 119, 47)
ORANGE_SOFT = (255, 241, 230)
WHITE = (255, 255, 255)
LINE = (216, 226, 235)

image = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(image)

try:
    regular = ImageFont.truetype("segoeui.ttf", 22)
    small = ImageFont.truetype("segoeui.ttf", 18)
    heading = ImageFont.truetype("segoeuib.ttf", 28)
    title = ImageFont.truetype("segoeuib.ttf", 54)
    metric = ImageFont.truetype("segoeuib.ttf", 36)
except OSError:
    regular = small = heading = title = metric = ImageFont.load_default()

def text(x, y, value, font=regular, fill=NAVY, anchor=None):
    draw.text((x, y), value, font=font, fill=fill, anchor=anchor)

def wrap(value, width, font):
    words, lines, line = value.split(), [], ""
    for word in words:
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

def paragraph(x, y, value, width, font=regular, fill=MUTED, gap=9):
    for line in wrap(value, width, font):
        text(x, y, line, font, fill)
        y += font.size + gap
    return y

def card(x, y, w, h, fill=WHITE, outline=LINE, radius=18):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=2)

def pill(x, y, w, label, fill, color):
    draw.rounded_rectangle((x, y, x + w, y + 34), radius=17, fill=fill)
    text(x + w / 2, y + 17, label, small, color, "mm")

# Header
draw.rounded_rectangle((48, 42, W - 48, 178), radius=28, fill=NAVY)
draw.rounded_rectangle((78, 74, 92, 146), radius=7, fill=TEAL)
text(124, 66, "GhostTrace", title, WHITE)
text(126, 130, "Evidence-first deletion auditing for distributed customer data", regular, (193, 212, 231))
pill(1260, 88, 235, "CLI-FIRST AGENT", TEAL, WHITE)

# Problem and definition
card(48, 212, 470, 292, WHITE)
pill(78, 242, 134, "THE PROBLEM", ORANGE_SOFT, ORANGE)
text(78, 298, "Deletion is not a button.", heading, NAVY)
paragraph(78, 348, "A workflow can report Complete while customer data remains in replicas, search indexes, analytics, support systems, exports, logs, backups, or active sync pipelines.", 390, regular)

card(548, 212, 1004, 260, TEAL_SOFT, (186, 230, 230))
pill(578, 242, 128, "THE IDEA", (199, 237, 237), TEAL)
text(578, 298, "GhostTrace proves the state of the data.", heading, NAVY)
paragraph(578, 348, "It resolves historical identities, reads evidence at the audit timestamp, applies retention rules, detects recreation paths, and generates the exact next steps needed to finish or verify a deletion request.", 900, regular)

# Pipeline
text(48, 520, "HOW IT WORKS", heading, NAVY)
steps = [
    (48, "01", "Resolve", "Current + historical identifiers", BLUE_SOFT, (55, 105, 174)),
    (344, "02", "Collect", "CSV, JSON, SQL, logs, media", TEAL_SOFT, TEAL),
    (640, "03", "Reconstruct", "State at audit_at cutoff", ORANGE_SOFT, ORANGE),
    (936, "04", "Apply policy", "Delete, redact, anonymize, retain", BLUE_SOFT, (55, 105, 174)),
    (1232, "05", "Prove", "Findings + remediation + checks", TEAL_SOFT, TEAL),
]
for x, number, name, detail, fill, accent in steps:
    card(x, 560, 260, 142, fill, fill)
    text(x + 24, 582, number, heading, accent)
    text(x + 24, 620, name, heading, NAVY)
    paragraph(x + 24, 660, detail, 210, small, MUTED, 5)
    if x < 1232:
        draw.line((x + 262, 631, x + 290, 631), fill=LINE, width=4)
        draw.polygon([(x + 300, 631), (x + 286, 623), (x + 286, 639)], fill=LINE)

# Output and metrics
card(48, 756, 740, 172, NAVY, NAVY)
text(78, 784, "OUTPUT", heading, (127, 226, 229))
text(78, 832, "COMPLETE", heading, WHITE)
text(270, 832, "INCOMPLETE", heading, WHITE)
text(500, 832, "NOT_APPLICABLE", heading, WHITE)
text(78, 876, "Ordered findings • safe remediation • verification proof", small, (193, 212, 231))

card(818, 756, 734, 172, WHITE, LINE)
text(850, 784, "MEASURED RESULTS", heading, NAVY)
text(850, 832, "518", metric, TEAL)
text(1010, 832, "96.88%", metric, ORANGE)
text(1212, 832, "73.54%", metric, (55, 105, 174))
text(850, 883, "cases generated", small, MUTED)
text(1010, 883, "public status accuracy", small, MUTED)
text(1212, 883, "public step F1", small, MUTED)

# Footer
text(48, 970, "Python • deterministic evidence engine • privacy engineering", small, MUTED)
text(W - 48, 970, "github.com/tanaygt/ghosttrace-deletion-audit", small, TEAL, "ra")

OUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUT, "PNG", optimize=True)
print(OUT)

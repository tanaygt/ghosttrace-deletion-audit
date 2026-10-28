from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture.png"
W, H = 1600, 900
image = Image.new("RGB", (W, H), (11, 16, 32))
draw = ImageDraw.Draw(image)

try:
    regular = ImageFont.truetype("segoeui.ttf", 22)
    medium = ImageFont.truetype("segoeuib.ttf", 28)
    title = ImageFont.truetype("segoeuib.ttf", 50)
except OSError:
    regular = medium = title = ImageFont.load_default()

draw.rounded_rectangle((24, 24, W - 24, H - 24), radius=32, fill=(22, 33, 61))
draw.text((90, 78), "GhostTrace", font=title, fill=(255, 255, 255))
draw.text((90, 140), "Evidence-first deletion auditing for distributed customer data", font=regular, fill=(169, 184, 214))
draw.rounded_rectangle((90, 190, W - 90, 194), radius=2, fill=(101, 217, 255))

boxes = [
    (90, 270, "01", "Requests", "Deletion intent + audit time"),
    (440, 270, "02", "Identity graph", "Current + historical identifiers"),
    (790, 270, "03", "Evidence intake", "CSV, JSON, SQL, logs, media"),
    (1140, 270, "04", "Temporal join", "State at audit_at cutoff"),
]
for x, y, number, heading, detail in boxes:
    draw.rounded_rectangle((x, y, x + 280, y + 150), radius=22, fill=(30, 49, 89), outline=(101, 217, 255), width=2)
    draw.text((x + 28, y + 25), number, font=regular, fill=(101, 217, 255))
    draw.text((x + 28, y + 65), heading, font=medium, fill=(255, 255, 255))
    draw.text((x + 28, y + 112), detail, font=regular, fill=(184, 199, 226))

draw.rounded_rectangle((485, 560, 1115, 710), radius=22, fill=(38, 54, 107), outline=(139, 124, 255), width=3)
draw.text((520, 590), "05", font=regular, fill=(185, 170, 255))
draw.text((520, 630), "Policy compiler", font=medium, fill=(255, 255, 255))
draw.text((520, 680), "Deletion rules + retention + recreation risks", font=regular, fill=(203, 211, 237))

def arrow(start, end):
    draw.line((start, end), fill=(124, 199, 232), width=4)
    x1, y1 = end
    draw.polygon([(x1, y1), (x1 - 14, y1 - 8), (x1 - 14, y1 + 8)], fill=(124, 199, 232))

arrow((370, 345), (430, 345))
arrow((720, 345), (780, 345))
arrow((1070, 345), (1130, 345))
arrow((1280, 420), (1280, 500))
arrow((1280, 500), (800, 500))
arrow((800, 500), (800, 550))
arrow((930, 420), (930, 550))

draw.text((90, 790), "Output", font=medium, fill=(255, 255, 255))
draw.text((90, 835), "Ordered findings  •  remediation  •  verification  •  validated output.csv", font=regular, fill=(169, 184, 214))
draw.text((1510, 835), "deterministic by default", font=regular, fill=(101, 217, 255), anchor="ra")

OUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUT, "PNG", optimize=True)
print(OUT)

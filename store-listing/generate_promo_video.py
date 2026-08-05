"""Niyetsen — Play Store tanıtım videosu (YouTube için 1920×1080, ~20 sn).

Akış: başlık kartı → 7 vitrin karesi (telefon solda, mesaj sağda) → CTA kartı.
Crossfade geçişler, 30fps, H.264. Müzik YOK — YouTube/CapCut'ta telifsiz
müzik eklenir (öneri: sakin akustik, 90-100 BPM).

Üret: cd store-listing && python3 generate_promo_video.py
Çıktı: video/niyetsen_promo_1920x1080.mp4  → YouTube'a 'liste dışı' yükle,
linki Play Console 'Tanıtım videosu' alanına yapıştır.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
GF = ROOT.parent / "mobile" / "node_modules" / "@expo-google-fonts"
BUILD = ROOT / "video" / "_slides"
OUT = ROOT / "video" / "niyetsen_promo_1920x1080.mp4"

W, H = 1920, 1080
INK = (31, 42, 30)
INK_SOFT = (74, 94, 70)
LEAF = (53, 129, 74)
CORAL = (224, 104, 66)
CREAM = (255, 252, 244)

SLIDE_SEC = 2.4
CARD_SEC = 2.8
FADE = 0.5

STORY = [
    ("01_niyet.png", "Niyetin konuşulur.", "Sohbetle çıkar, plana döner."),
    ("02_sohbet.png", "Rehber seni hatırlar", "Her sohbet kaldığı yerden."),
    ("03_plan.png", "Her gün görselli plan", "Görevler hayatından türer."),
    ("04_kanit.png", "Fotoğrafla kanıtla", "Oyun adil kalır."),
    ("05_zincir.png", "Zincirini koru", "Gün gün büyü. 🌱"),
    ("06_rapor.png", "Yolculuğunu gör", "Wrapped tarzı raporun."),
    ("07_basla.png", "Bugün ilk adımını at", "Niyetsen — yaşam asistanın."),
]


def _font(family: str, size: int) -> ImageFont.FreeTypeFont:
    paths = {
        "display": GF / "fraunces" / "600SemiBold" / "Fraunces_600SemiBold.ttf",
        "bold": GF / "manrope" / "800ExtraBold" / "Manrope_800ExtraBold.ttf",
        "medium": GF / "manrope" / "500Medium" / "Manrope_500Medium.ttf",
    }
    return ImageFont.truetype(str(paths[family]), size)


def _bg() -> Image.Image:
    bg = Image.open(ROOT / "sources" / "store-bg-spring-soft.png").convert("RGB")
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * scale), round(bg.height * scale)), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    canvas = bg.crop((left, top, left + W, top + H)).filter(
        ImageFilter.GaussianBlur(6)
    )
    wash = Image.new("RGBA", (W, H), (255, 253, 246, 150))
    return Image.alpha_composite(canvas.convert("RGBA"), wash)


def _logo_tile(size: int) -> tuple[Image.Image, Image.Image]:
    logo = Image.open(ROOT / "sources" / "logo.png").convert("RGBA")
    logo = logo.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size, size], radius=size // 4, fill=255
    )
    return logo, mask


def title_card() -> Image.Image:
    canvas = _bg()
    logo, mask = _logo_tile(220)
    canvas.paste(logo, ((W - 220) // 2, 250), mask)
    draw = ImageDraw.Draw(canvas)
    t = "Niyetsen"
    tf = _font("display", 120)
    draw.text(((W - draw.textlength(t, font=tf)) / 2, 520), t, font=tf, fill=INK)
    s = "Niyetini söze, sözünü zincire çevir."
    sf = _font("medium", 44)
    draw.text(((W - draw.textlength(s, font=sf)) / 2, 690), s, font=sf, fill=INK_SOFT)
    return canvas


def end_card() -> Image.Image:
    canvas = _bg()
    draw = ImageDraw.Draw(canvas)
    t = "Bugün ilk adımını at"
    tf = _font("display", 96)
    draw.text(((W - draw.textlength(t, font=tf)) / 2, 380), t, font=tf, fill=INK)
    pill = "Google Play'de Niyetsen"
    pf = _font("bold", 42)
    pw = draw.textlength(pill, font=pf) + 96
    px, py = (W - pw) / 2, 560
    draw.rounded_rectangle([px, py, px + pw, py + 96], radius=48, fill=LEAF)
    draw.text((px + 48, py + 22), pill, font=pf, fill=CREAM)
    return canvas


def slide(shot_name: str, headline: str, sub: str) -> Image.Image:
    canvas = _bg()
    shot = Image.open(ROOT / "phone" / "play_1080x1920" / shot_name).convert("RGB")
    ph = 940
    pw = round(shot.width * ph / shot.height)
    shot = shot.resize((pw, ph), Image.LANCZOS)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw, ph], radius=42, fill=255)
    sx, sy = 190, (H - ph) // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [sx + 6, sy + 16, sx + pw + 6, sy + ph + 16], radius=42, fill=(46, 90, 47, 80)
    )
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.paste(shot, (sx, sy), mask)

    draw = ImageDraw.Draw(canvas)
    tx = sx + pw + 110
    tf = _font("display", 76)
    words, lines, cur = headline.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=tf) > W - tx - 120 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    ty = H // 2 - len(lines) * 48 - 40
    for line in lines:
        draw.text((tx, ty), line, font=tf, fill=INK)
        ty += 96
    draw.text((tx + 4, ty + 18), sub, font=_font("medium", 40), fill=INK_SOFT)
    return canvas


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    frames: list[tuple[Path, float]] = []

    def save(img: Image.Image, name: str, dur: float) -> None:
        path = BUILD / name
        img.convert("RGB").save(path, quality=92)
        frames.append((path, dur))

    save(title_card(), "00_title.jpg", CARD_SEC)
    for i, (shot, headline, sub) in enumerate(STORY, start=1):
        save(slide(shot, headline, sub), f"{i:02d}_slide.jpg", SLIDE_SEC)
    save(end_card(), "99_end.jpg", CARD_SEC)

    # ffmpeg xfade zinciri
    inputs, filters = [], []
    for path, dur in frames:
        inputs += ["-loop", "1", "-t", str(dur), "-i", str(path)]
    offset = 0.0
    prev = "[0:v]"
    for i in range(1, len(frames)):
        offset += frames[i - 1][1] - FADE
        out = f"[v{i}]"
        filters.append(
            f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}{out}"
        )
        prev = out
    filter_complex = ";".join(filters) + f";{prev}format=yuv420p[vout]"

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex, "-map", "[vout]",
        "-c:v", "libx264", "-r", "30", "-crf", "20", "-preset", "medium",
        str(OUT),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    total = sum(d for _, d in frames) - FADE * (len(frames) - 1)
    print(f"OK → {OUT} (~{total:.0f} sn, {OUT.stat().st_size // (1024*1024)} MB)")


if __name__ == "__main__":
    main()

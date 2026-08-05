#!/usr/bin/env python3
"""
Niyetsen — Play Store + App Store önizleme görselleri üretici.

Türkçe metin Pillow ile çizilir (AI yazı YASAK — bozuk çıkar).
Çıktılar:
  phone/play_1080x1920/   → Google Play (önerilen)
  phone/ios_1290x2796/    → App Store iPhone 6.7"
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources"
OUT_PLAY = ROOT / "phone" / "play_1080x1920"
OUT_IOS = ROOT / "phone" / "ios_1290x2796"

# İlkbahar token'ları (theme.ts)
CREAM = (248, 249, 243)
LEAF = (61, 122, 78)
LEAF_DEEP = (47, 107, 62)
CORAL = (217, 106, 69)
TEXT = (28, 36, 28)
TEXT_MUTED = (94, 107, 88)
WHITE = (255, 255, 255)
CARD = (255, 255, 255)
SOFT_DARK = (28, 36, 27)

# Marka tipografisi (uygulamayla birebir): Manrope. node_modules'tan okunur —
# hem macOS hem CI/sandbox'ta çalışır. Arial yalnız son çare.
_ROOT = Path(__file__).resolve().parents[1]
_GF = _ROOT / "mobile" / "node_modules" / "@expo-google-fonts"
FONT_CANDIDATES_REG = [
    str(_GF / "manrope" / "500Medium" / "Manrope_500Medium.ttf"),
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
FONT_CANDIDATES_BOLD = [
    str(_GF / "manrope" / "800ExtraBold" / "Manrope_800ExtraBold.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
FONT_UNI = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES_REG):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.truetype(FONT_UNI, size)


def load_bg(name: str, size: tuple[int, int]) -> Image.Image:
    path = SRC / name
    img = Image.open(path).convert("RGB")
    img = img.resize(size, Image.Resampling.LANCZOS)
    # Marka üzerine hafif krem yıkama — okunurluk
    wash = Image.new("RGB", size, CREAM)
    return Image.blend(img, wash, 0.28)


def round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill,
    outline=None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap_text(text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if fnt.getlength(trial) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_headline(
    canvas: Image.Image,
    title: str,
    subtitle: str,
    *,
    y: int,
    max_w: int,
    title_size: int,
    sub_size: int,
) -> int:
    draw = ImageDraw.Draw(canvas)
    tw = canvas.width
    title_f = font(title_size, bold=True)
    sub_f = font(sub_size, bold=False)
    x0 = (tw - max_w) // 2
    lines = wrap_text(title, title_f, max_w)
    cy = y
    for line in lines:
        lw = title_f.getlength(line)
        draw.text(((tw - lw) / 2, cy), line, font=title_f, fill=TEXT)
        cy += int(title_size * 1.18)
    cy += int(title_size * 0.22)
    for line in wrap_text(subtitle, sub_f, max_w):
        lw = sub_f.getlength(line)
        draw.text(((tw - lw) / 2, cy), line, font=sub_f, fill=TEXT_MUTED)
        cy += int(sub_size * 1.25)
    return cy


def phone_frame(w: int, h: int) -> Image.Image:
    """Minimal modern phone bezel + screen area."""
    phone = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(phone)
    # shadow
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((8, 14, w - 2, h - 2), radius=54, fill=(20, 30, 20, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    phone = Image.alpha_composite(phone, shadow)
    d = ImageDraw.Draw(phone)
    # body
    d.rounded_rectangle((0, 0, w - 10, h - 16), radius=48, fill=(24, 28, 24, 255))
    # screen inset
    inset = 10
    d.rounded_rectangle(
        (inset, inset + 4, w - 10 - inset, h - 16 - inset),
        radius=40,
        fill=(*CREAM, 255),
    )
    # dynamic island
    cx = (w - 10) // 2
    d.rounded_rectangle((cx - 52, 22, cx + 52, 48), radius=16, fill=(18, 20, 18, 255))
    return phone


def paste_phone(base: Image.Image, content: Image.Image, top: int) -> None:
    # Scale phone to ~62% of canvas width
    pw = int(base.width * 0.62)
    scale = pw / content.width
    ph = int(content.height * scale)
    phone = content.resize((pw, ph), Image.Resampling.LANCZOS)
    frame = phone_frame(pw + 20, ph + 36)
    # place screen into frame
    composed = frame.copy()
    # screen area roughly inset
    screen = phone.resize(
        (pw - 8, ph - 8), Image.Resampling.LANCZOS
    ).convert("RGBA")
    composed.paste(screen, (14, 22), screen)
    x = (base.width - composed.width) // 2
    base.paste(composed, (x, top), composed)


def ui_chat(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    # header
    d.rectangle((0, 0, w, 72), fill=WHITE)
    d.text((24, 24), "Niyetsen", font=font(26, True), fill=LEAF_DEEP)
    d.text((24, 52), "Rehberin dinliyor", font=font(16), fill=TEXT_MUTED)
    bubbles = [
        ("user", "Bu yıl disiplinli bir sporcu gibi yaşamak istiyorum."),
        ("ai", "Güzel. Sabah ritüeli mi, yoksa antrenman mı önce gelsin?"),
        ("user", "Sabah 20 dk yürüyüş + akşam kuvvet."),
        ("ai", "Tamam. Bunu görselli 14 günlük plana çevirebilirim."),
    ]
    y = 96
    for role, text in bubbles:
        f = font(17)
        lines = wrap_text(text, f, int(w * 0.62))
        bh = 22 + len(lines) * 22
        bw = int(w * 0.72)
        if role == "user":
            x0 = w - bw - 20
            fill = (228, 239, 228)
        else:
            x0 = 20
            fill = WHITE
        round_rect(d, (x0, y, x0 + bw, y + bh), 18, fill, outline=(226, 232, 216))
        ty = y + 12
        for line in lines:
            d.text((x0 + 14, ty), line, font=f, fill=TEXT)
            ty += 22
        y += bh + 14
    # composer
    round_rect(d, (16, h - 70, w - 16, h - 18), 22, WHITE, outline=(226, 232, 216))
    d.text((34, h - 52), "Niyetini yaz…", font=font(17), fill=TEXT_MUTED)
    return img


def ui_plan(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    d.text((24, 28), "Planım", font=font(28, True), fill=TEXT)
    d.text((24, 64), "Sporcu yazı · Gün 3", font=font(16), fill=TEXT_MUTED)
    cards = [
        ("Sabah 20 dk yürüyüş", "İstikrar · +50", LEAF),
        ("Akşam kuvvet antrenmanı", "Disiplin · +50", CORAL),
        ("Akşam meyve tabağı", "Özsaygı · bekliyor", TEXT_MUTED),
    ]
    y = 100
    for title, meta, accent in cards:
        round_rect(d, (20, y, w - 20, y + 118), 22, WHITE, outline=(226, 232, 216))
        # image placeholder strip
        d.rounded_rectangle((32, y + 16, 118, y + 100), radius=14, fill=(228, 239, 228))
        d.ellipse((52, y + 36, 98, y + 82), fill=accent)
        d.text((136, y + 28), title, font=font(18, True), fill=TEXT)
        d.text((136, y + 58), meta, font=font(15), fill=TEXT_MUTED)
        y += 132
    return img


def ui_proof(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    d.text((24, 28), "Bugün", font=font(28, True), fill=TEXT)
    d.text((24, 64), "Kanıtla · görev onaylanır", font=font(16), fill=TEXT_MUTED)
    # camera preview mock
    round_rect(d, (28, 110, w - 28, h - 160), 28, (40, 52, 40))
    d.ellipse((w // 2 - 40, h // 2 - 30, w // 2 + 40, h // 2 + 50), outline=(180, 200, 170), width=3)
    d.text((w // 2 - 70, h // 2 + 70), "Fotoğraf çek", font=font(16), fill=(200, 220, 195))
    round_rect(d, (40, h - 130, w - 40, h - 40), 20, WHITE)
    d.text((56, h - 108), "Akşam meyve tabağı", font=font(18, True), fill=TEXT)
    d.text((56, h - 78), "Doğru fotoğraf → onay · adil oyun", font=font(14), fill=TEXT_MUTED)
    return img


def ui_streak(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    d.text((24, 28), "Zincir", font=font(28, True), fill=TEXT)
    # big number
    big = font(96, True)
    num = "23"
    nw = big.getlength(num)
    d.text(((w - nw) / 2, 140), num, font=big, fill=LEAF_DEEP)
    d.text(((w - 220) / 2, 260), "gün kesintisiz", font=font(22), fill=TEXT_MUTED)
    # ring
    cx, cy, r = w // 2, 200, 120
    d.arc((cx - r, cy - r, cx + r, cy + r), start=200, end=520, fill=CORAL, width=10)
    # categories
    cats = [("İrade", 72), ("Disiplin", 64), ("İstikrar", 80)]
    y = 340
    for name, pct in cats:
        d.text((40, y), name, font=font(16, True), fill=TEXT)
        round_rect(d, (40, y + 28, w - 40, y + 44), 8, (232, 236, 221))
        fill_w = int((w - 80) * pct / 100)
        round_rect(d, (40, y + 28, 40 + fill_w, y + 44), 8, LEAF)
        y += 70
    return img


def ui_rapor(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), (245, 236, 228))
    d = ImageDraw.Draw(img)
    d.text((24, 36), "Raporun", font=font(28, True), fill=TEXT)
    d.text((24, 72), "14 günde büyüdüğün yerler", font=font(16), fill=TEXT_MUTED)
    round_rect(d, (28, 130, w - 28, 320), 28, WHITE)
    d.text((48, 160), "42 görev tamamlandı", font=font(22, True), fill=LEAF_DEEP)
    d.text((48, 200), "En güçlü: İstikrar", font=font(18), fill=TEXT)
    d.text((48, 240), "Zincir rekoru: 23 gün", font=font(18), fill=TEXT)
    d.text((48, 280), "Yalnız kazanımlar — utandırma yok", font=font(14), fill=TEXT_MUTED)
    round_rect(d, (28, 350, w - 28, 480), 28, (255, 232, 218))
    d.text((48, 390), "Paylaş · hikâyene dönüştür", font=font(18, True), fill=CORAL)
    return img


def ui_hero_mark(w: int, h: int, logo: Image.Image) -> Image.Image:
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    # soft circles
    for i, (cx, cy, r, c) in enumerate(
        [
            (w * 0.2, h * 0.25, 90, (228, 239, 228)),
            (w * 0.8, h * 0.35, 70, (255, 232, 218)),
            (w * 0.5, h * 0.7, 110, (232, 236, 221)),
        ]
    ):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    logo_s = logo.resize((220, 220), Image.Resampling.LANCZOS).convert("RGBA")
    # white circle behind logo
    badge = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.ellipse((0, 0, 259, 259), fill=(255, 255, 255, 255))
    img.paste(badge, ((w - 260) // 2, h // 2 - 160), badge)
    img.paste(logo_s, ((w - 220) // 2, h // 2 - 140), logo_s)
    d = ImageDraw.Draw(img)
    d.text(((w - 160) / 2, h // 2 + 100), "Niyetsen", font=font(28, True), fill=TEXT)
    d.text(((w - 240) / 2, h // 2 + 140), "yaşam asistanın", font=font(16), fill=TEXT_MUTED)
    return img


def add_logo_badge(canvas: Image.Image, logo: Image.Image) -> None:
    size = 56
    l = logo.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    canvas.paste(l, (canvas.width - size - 36, 36), l)


def build_slide(
    bg_name: str,
    title: str,
    subtitle: str,
    ui: Image.Image,
    size: tuple[int, int],
    logo: Image.Image,
) -> Image.Image:
    W, H = size
    canvas = load_bg(bg_name, size)
    # scale typography to canvas
    title_size = max(36, int(W * 0.055))
    sub_size = max(18, int(W * 0.028))
    max_w = int(W * 0.86)
    y_after = draw_headline(
        canvas, title, subtitle, y=int(H * 0.06), max_w=max_w,
        title_size=title_size, sub_size=sub_size,
    )
    phone_top = min(y_after + int(H * 0.03), int(H * 0.28))
    paste_phone(canvas, ui, phone_top)
    add_logo_badge(canvas, logo)
    # bottom safe caption strip hint (store crops)
    return canvas.convert("RGB")


def export_pair(name: str, slide_play: Image.Image, slide_ios: Image.Image) -> None:
    OUT_PLAY.mkdir(parents=True, exist_ok=True)
    OUT_IOS.mkdir(parents=True, exist_ok=True)
    p = OUT_PLAY / f"{name}.png"
    i = OUT_IOS / f"{name}.png"
    slide_play.save(p, "PNG", optimize=True)
    slide_ios.save(i, "PNG", optimize=True)
    print(f"wrote {p.name}  play={slide_play.size}  ios={slide_ios.size}")


def main() -> None:
    logo = Image.open(SRC / "logo.png").convert("RGBA")
    story = [
        (
            "01_niyet",
            "store-bg-dawn-cream.png",
            "Niyetin konuşulur.\nPlanın yaşanır.",
            "Sohbetle çıkar, görselli plana döner.",
            "hero",
        ),
        (
            "02_sohbet",
            "store-bg-spring-soft.png",
            "Sohbetle niyetini netleştir",
            "Rehber hatırlar — sen tekrar anlatmazsın.",
            "chat",
        ),
        (
            "03_plan",
            "store-bg-dawn-cream.png",
            "Her gün görselli bir plan",
            "Görevler hayatından türer — uydurma değil.",
            "plan",
        ),
        (
            "04_kanit",
            "store-bg-spring-soft.png",
            "Fotoğrafla kanıtla",
            "Doğru kare onaylanır. Oyun adil kalır.",
            "proof",
        ),
        (
            "05_zincir",
            "store-bg-forest-soft.png",
            "Zincirini koru",
            "Gün gün büyü. Kaçırınca dürüst yüzleşme.",
            "streak",
        ),
        (
            "06_rapor",
            "store-bg-dawn-cream.png",
            "Yolculuğunu gör",
            "Wrapped tarzı rapor — yalnız kazanımlar.",
            "rapor",
        ),
        (
            "07_basla",
            "store-bg-spring-soft.png",
            "Bugün ilk adımını at",
            "Niyetsen — yaşam asistanın.",
            "hero",
        ),
    ]

    for name, bg, title, sub, kind in story:
        for label, size, out_fn in (
            ("play", (1080, 1920), None),
            ("ios", (1290, 2796), None),
        ):
            # UI canvas size inside phone (logical)
            ui_w, ui_h = 390, 780
            if kind == "hero":
                ui = ui_hero_mark(ui_w, ui_h, logo)
            elif kind == "chat":
                ui = ui_chat(ui_w, ui_h)
            elif kind == "plan":
                ui = ui_plan(ui_w, ui_h)
            elif kind == "proof":
                ui = ui_proof(ui_w, ui_h)
            elif kind == "streak":
                ui = ui_streak(ui_w, ui_h)
            else:
                ui = ui_rapor(ui_w, ui_h)
            slide = build_slide(bg, title.replace("\n", " "), sub, ui, size, logo)
            # For titles with newline intent on hero — redraw first slide specially
            if kind == "hero" and "Niyetin" in title:
                # Rebuild with two-line headline
                W, H = size
                canvas = load_bg(bg, size)
                title_size = max(38, int(W * 0.058))
                sub_size = max(18, int(W * 0.028))
                draw = ImageDraw.Draw(canvas)
                tf = font(title_size, True)
                sf = font(sub_size)
                lines = ["Niyetin konuşulur.", "Planın yaşanır."]
                cy = int(H * 0.07)
                for line in lines:
                    lw = tf.getlength(line)
                    draw.text(((W - lw) / 2, cy), line, font=tf, fill=TEXT)
                    cy += int(title_size * 1.2)
                cy += 8
                for line in wrap_text(sub, sf, int(W * 0.86)):
                    lw = sf.getlength(line)
                    draw.text(((W - lw) / 2, cy), line, font=sf, fill=TEXT_MUTED)
                    cy += int(sub_size * 1.25)
                paste_phone(canvas, ui, min(cy + 20, int(H * 0.28)))
                add_logo_badge(canvas, logo)
                slide = canvas.convert("RGB")
            if label == "play":
                play_img = slide
            else:
                export_pair(name, play_img, slide)

    print("OK — store screenshots ready.")


if __name__ == "__main__":
    main()

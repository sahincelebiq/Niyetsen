"""Niyetsen — Play Store feature graphic (1024×500), v2 'İlkbahar'.

v1 sorunu: açık zeminde beyaz slogan okunmuyordu. v2: yumuşak krem panel +
koyu yaprak tipografi (Fraunces başlık, Manrope gövde) + akış çipleri.
Üret: cd store-listing && python3 generate_feature_graphic.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
GF = ROOT.parent / "mobile" / "node_modules" / "@expo-google-fonts"

W, H = 1024, 500
INK = (31, 42, 30)          # koyu yaprak (#1F2A1E)
INK_SOFT = (74, 94, 70)
LEAF = (53, 129, 74)        # #35814A
CORAL = (224, 104, 66)      # #E06842
CREAM = (255, 252, 244)


def _font(family: str, size: int) -> ImageFont.FreeTypeFont:
    paths = {
        "display": GF / "fraunces" / "600SemiBold" / "Fraunces_600SemiBold.ttf",
        "bold": GF / "manrope" / "800ExtraBold" / "Manrope_800ExtraBold.ttf",
        "medium": GF / "manrope" / "500Medium" / "Manrope_500Medium.ttf",
    }
    try:
        return ImageFont.truetype(str(paths[family]), size)
    except OSError:
        return ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size
        )


def main() -> None:
    bg = Image.open(ROOT / "sources" / "store-bg-spring-soft.png").convert("RGB")
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * scale), round(bg.height * scale)), Image.LANCZOS)
    left = (bg.width - W) // 2
    top = (bg.height - H) // 2
    canvas = bg.crop((left, top, left + W, top + H)).convert("RGBA")

    # Okunurluk paneli: sol 2/3'e yumuşak krem yıkama (degrade)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for x in range(W):
        alpha = 210 if x < 620 else max(0, 210 - int((x - 620) * (210 / 260)))
        odraw.line([(x, 0), (x, H)], fill=(255, 253, 246, alpha))
    canvas = Image.alpha_composite(canvas, overlay)

    # Logo karosu (yumuşak gölgeli)
    logo = Image.open(ROOT / "sources" / "logo.png").convert("RGBA")
    tile = 176
    logo = logo.resize((tile, tile), Image.LANCZOS)
    mask = Image.new("L", (tile, tile), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile, tile], radius=40, fill=255)
    lx, ly = 78, (H - tile) // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [lx + 4, ly + 10, lx + tile + 4, ly + tile + 10], radius=40,
        fill=(46, 90, 47, 70),
    )
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(12)))
    canvas.paste(logo, (lx, ly), mask)
    draw = ImageDraw.Draw(canvas)

    # Metin bloğu
    tx = lx + tile + 56
    draw.text((tx, 118), "Niyetsen", font=_font("display", 88), fill=INK)
    draw.text(
        (tx + 4, 238),
        "Niyetini söze, sözünü zincire çevir.",
        font=_font("medium", 33),
        fill=INK_SOFT,
    )

    # Akış çipleri: Sohbet → Plan → Kanıt → Zincir
    chips = [("Sohbet", LEAF), ("Plan", LEAF), ("Kanıt", CORAL), ("Zincir", CORAL)]
    cx, cy = tx + 4, 314
    chip_font = _font("bold", 26)
    arrow_font = _font("medium", 30)
    for i, (label, color) in enumerate(chips):
        tw = draw.textlength(label, font=chip_font)
        pad = 22
        draw.rounded_rectangle(
            [cx, cy, cx + tw + pad * 2, cy + 52], radius=26, fill=color
        )
        draw.text((cx + pad, cy + 11), label, font=chip_font, fill=CREAM)
        cx += tw + pad * 2 + 14
        if i < len(chips) - 1:
            draw.text((cx, cy + 8), "→", font=arrow_font, fill=INK_SOFT)
            cx += draw.textlength("→", font=arrow_font) + 14

    out = ROOT / "feature" / "feature_1024x500.png"
    canvas.convert("RGB").save(out, optimize=True)
    print(f"OK → {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

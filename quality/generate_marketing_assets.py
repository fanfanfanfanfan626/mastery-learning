from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOC_ASSETS = ROOT / "docs" / "assets"
PLUGIN_ASSETS = ROOT / "plugins" / "mastery-learning" / "assets"

INK = "#F8FAFC"
MUTED = "#A7B0C5"
PANEL = "#111B31"
PURPLE = "#7767FF"
CYAN = "#36D9C4"
GREEN = "#5DE39A"
AMBER = "#F7C66B"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def background(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, "#07101F")
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            glow_a = max(
                0.0,
                1.0
                - ((x - width * 0.78) ** 2 + (y - height * 0.15) ** 2) ** 0.5
                / (width * 0.75),
            )
            glow_b = max(
                0.0,
                1.0
                - ((x - width * 0.15) ** 2 + (y - height * 0.86) ** 2) ** 0.5
                / (width * 0.6),
            )
            pixels[x, y] = (
                int(7 + 25 * glow_a + 3 * glow_b),
                int(16 + 12 * glow_a + 18 * glow_b),
                int(31 + 38 * glow_a + 30 * glow_b),
            )
    return image


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    radius: int = 24,
    outline: str | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def logo_mark(size: int = 512, *, dark: bool = False) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = int(size * 0.08)
    rounded(
        draw,
        (pad, pad, size - pad, size - pad),
        "#0B1427" if dark else "#101A33",
        radius=int(size * 0.22),
        outline="#8377FF",
        width=max(2, size // 80),
    )
    draw.arc(
        (size * 0.19, size * 0.19, size * 0.81, size * 0.81),
        205,
        515,
        fill=CYAN,
        width=max(8, size // 20),
    )
    draw.ellipse(
        (size * 0.68, size * 0.16, size * 0.78, size * 0.26),
        fill=GREEN,
    )
    draw.line(
        (
            size * 0.28,
            size * 0.67,
            size * 0.28,
            size * 0.37,
            size * 0.5,
            size * 0.61,
            size * 0.72,
            size * 0.37,
            size * 0.72,
            size * 0.67,
        ),
        fill=INK,
        width=max(10, size // 22),
        joint="curve",
    )
    return image


def pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str) -> int:
    label_font = font(22, bold=True)
    bbox = draw.textbbox((0, 0), text, font=label_font)
    width = bbox[2] - bbox[0] + 36
    rounded(
        draw,
        (x, y, x + width, y + 44),
        "#121F38",
        radius=22,
        outline=color,
        width=2,
    )
    draw.text((x + 18, y + 8), text, font=label_font, fill=color)
    return x + width + 12


def social_preview() -> Image.Image:
    image = background((1280, 640))
    draw = ImageDraw.Draw(image)
    mark = logo_mark(172, dark=True)
    image.paste(mark, (76, 76), mark)
    draw.text((284, 84), "Mastery Learning", font=font(68, bold=True), fill=INK)
    draw.text((286, 168), "AI Teaching Skill", font=font(40, bold=True), fill=PURPLE)
    draw.text(
        (78, 286),
        "Beautiful HTML teaching. Durable mastery.",
        font=font(38, bold=True),
        fill=INK,
    )
    draw.text(
        (78, 350),
        "HTML classroom  ·  Interactive labs  ·  Evidence-based review",
        font=font(25),
        fill=MUTED,
    )
    x = 78
    for text, color in [
        ("LOCAL-FIRST", CYAN),
        ("OPEN SOURCE", GREEN),
        ("NO TELEMETRY", AMBER),
    ]:
        x = pill(draw, x, 426, text, color)
    draw.text(
        (80, 522),
        "github.com/fanfanfanfanfan626/mastery-learning",
        font=font(23),
        fill="#8792AB",
    )
    rounded(
        draw,
        (934, 276, 1200, 532),
        PANEL,
        radius=30,
        outline="#2B3B5D",
        width=2,
    )
    draw.text((970, 310), "Goal", font=font(24, bold=True), fill=PURPLE)
    draw.line((1008, 354, 1008, 459), fill="#435272", width=4)
    for y, label, color in [
        (372, "Lesson", CYAN),
        (420, "Practice", AMBER),
        (468, "Mastery", GREEN),
    ]:
        draw.ellipse((995, y - 8, 1021, y + 18), fill=color)
        draw.text((1043, y - 9), label, font=font(22, bold=True), fill=INK)
    return image


def lesson_screenshot() -> Image.Image:
    image = background((1280, 720))
    draw = ImageDraw.Draw(image)
    rounded(
        draw,
        (42, 34, 1238, 686),
        "#0D172A",
        radius=30,
        outline="#273856",
        width=2,
    )
    draw.ellipse((72, 64, 88, 80), fill="#FF6B6B")
    draw.ellipse((98, 64, 114, 80), fill=AMBER)
    draw.ellipse((124, 64, 140, 80), fill=GREEN)
    draw.text(
        (174, 54),
        "Mastery Learning · Attention Lab",
        font=font(25, bold=True),
        fill=INK,
    )
    rounded(draw, (74, 118, 485, 638), "#121E35", radius=22)
    draw.text((104, 148), "TODAY'S TARGET", font=font(18, bold=True), fill=PURPLE)
    draw.multiline_text(
        (104, 185),
        "See how attention\nchanges with temperature",
        font=font(34, bold=True),
        fill=INK,
        spacing=8,
    )
    draw.text((104, 286), "1  Predict", font=font(24, bold=True), fill=CYAN)
    draw.text((104, 334), "2  Manipulate", font=font(24, bold=True), fill=AMBER)
    draw.text((104, 382), "3  Explain", font=font(24, bold=True), fill=GREEN)
    draw.text((104, 430), "4  Transfer", font=font(24, bold=True), fill="#FF91C8")
    rounded(
        draw,
        (104, 520, 445, 588),
        "#172A43",
        radius=16,
        outline=PURPLE,
        width=2,
    )
    draw.text(
        (131, 539),
        "Evidence saved after review",
        font=font(19, bold=True),
        fill=INK,
    )
    rounded(draw, (520, 118, 1204, 488), "#111D32", radius=22)
    draw.text((554, 148), "Attention weights", font=font(26, bold=True), fill=INK)
    bars = [0.18, 0.34, 0.72, 0.49, 0.26]
    colors = ["#4E6EAF", "#5A84C8", PURPLE, CYAN, "#4E6EAF"]
    for index, value in enumerate(bars):
        x = 564 + index * 118
        y = 432 - int(value * 260)
        rounded(draw, (x, y, x + 72, 432), colors[index], radius=16)
        draw.text((x + 21, 446), str(index + 1), font=font(18, bold=True), fill=MUTED)
    rounded(draw, (520, 518, 1204, 638), "#121E35", radius=22)
    draw.text((550, 544), "Temperature", font=font(21, bold=True), fill=INK)
    draw.line((710, 566, 1012, 566), fill="#415170", width=8)
    draw.ellipse((844, 548, 880, 584), fill=PURPLE)
    rounded(draw, (1050, 538, 1170, 602), PURPLE, radius=18)
    draw.text((1071, 556), "Check", font=font(21, bold=True), fill=INK)
    return image


def demo_frame(step: int) -> Image.Image:
    image = background((960, 540))
    draw = ImageDraw.Draw(image)
    draw.text((48, 32), "Mastery Learning", font=font(27, bold=True), fill=INK)
    draw.text((272, 36), "AI Teaching Skill", font=font(20, bold=True), fill=PURPLE)
    titles = [
        "Say what you want to learn",
        "Set up once in a clear HTML card",
        "Learn inside one beautiful classroom",
        "Practice, explain, and transfer",
        "Save evidence — not vibes",
        "Continue from durable progress",
    ]
    subtitles = [
        "“I want to understand and train large language models.”",
        "One compact launch card · no entrance exam",
        "Orientation first · annotated code · visible relationships",
        "Hints fade while learner ownership grows",
        "Independent work + delayed recall + changed context",
        "Local-first · open source · no hidden telemetry",
    ]
    draw.text((48, 94), titles[step], font=font(40, bold=True), fill=INK)
    draw.text((50, 150), subtitles[step], font=font(22), fill=MUTED)
    rounded(
        draw,
        (48, 205, 912, 465),
        PANEL,
        radius=28,
        outline="#293C5F",
        width=2,
    )
    if step == 0:
        rounded(draw, (88, 250, 694, 338), "#182640", radius=22)
        draw.text(
            (118, 276),
            "I want to learn machine learning and LLMs.",
            font=font(25),
            fill=INK,
        )
        rounded(draw, (724, 360, 860, 416), PURPLE, radius=18)
        draw.text((756, 374), "Start", font=font(22, bold=True), fill=INK)
    elif step == 1:
        labels = [
            ("Beginner", CYAN),
            ("30 min/day", PURPLE),
            ("Guided", GREEN),
            ("No exam", AMBER),
        ]
        x, y = 88, 248
        for label, color in labels:
            x = pill(draw, x, y, label, color)
            if x > 700:
                x, y = 88, y + 68
        draw.text(
            (90, 392),
            "One reply → lesson begins",
            font=font(24, bold=True),
            fill=INK,
        )
    elif step == 2:
        for index, height in enumerate([48, 94, 172, 126, 70]):
            x = 112 + index * 108
            rounded(
                draw,
                (x, 414 - height, x + 64, 414),
                ["#4E6EAF", "#5A84C8", PURPLE, CYAN, "#4E6EAF"][index],
                radius=14,
            )
        draw.text((680, 250), "Predict", font=font(22, bold=True), fill=CYAN)
        draw.text((680, 302), "Change", font=font(22, bold=True), fill=AMBER)
        draw.text((680, 354), "Explain", font=font(22, bold=True), fill=GREEN)
    elif step == 3:
        tasks = [
            ("Predict before running", True),
            ("Change one condition", True),
            ("Explain the result", True),
            ("Transfer to a new case", False),
        ]
        for index, (label, done) in enumerate(tasks):
            y = 248 + index * 50
            draw.ellipse(
                (92, y, 120, y + 28),
                fill=GREEN if done else "#253654",
                outline=GREEN,
                width=2,
            )
            if done:
                draw.text((99, y - 2), "✓", font=font(21, bold=True), fill="#07101F")
            draw.text(
                (142, y - 3),
                label,
                font=font(23, bold=done),
                fill=INK if done else MUTED,
            )
    elif step == 4:
        states = [
            ("Guided practice", "observed", AMBER),
            ("Independent explanation", "passed", CYAN),
            ("Delayed recall", "due", PURPLE),
            ("Transfer", "passed", GREEN),
        ]
        for index, (label, status, color) in enumerate(states):
            y = 244 + index * 50
            draw.text((92, y), label, font=font(21, bold=True), fill=INK)
            rounded(
                draw,
                (650, y - 4, 820, y + 34),
                "#17253E",
                radius=17,
                outline=color,
                width=2,
            )
            draw.text(
                (686, y + 3),
                status.upper(),
                font=font(17, bold=True),
                fill=color,
            )
    else:
        rounded(draw, (88, 244, 386, 410), "#14233B", radius=22)
        draw.text((116, 274), "CURRENT PATH", font=font(17, bold=True), fill=PURPLE)
        draw.text((116, 316), "Python → NumPy", font=font(28, bold=True), fill=INK)
        draw.text((116, 360), "2 reviews due", font=font(21), fill=AMBER)
        rounded(draw, (430, 244, 868, 410), "#14233B", radius=22)
        draw.text((460, 274), "NEXT SESSION", font=font(17, bold=True), fill=CYAN)
        draw.text(
            (460, 316),
            "Resume from local progress",
            font=font(25, bold=True),
            fill=INK,
        )
        draw.text((460, 360), "No setup repeated", font=font(21), fill=MUTED)
    for index in range(6):
        color = PURPLE if index == step else "#31415F"
        draw.ellipse((408 + index * 28, 494, 420 + index * 28, 506), fill=color)
    return image


def main() -> None:
    DOC_ASSETS.mkdir(parents=True, exist_ok=True)
    PLUGIN_ASSETS.mkdir(parents=True, exist_ok=True)
    social_preview().save(DOC_ASSETS / "social-preview.png", optimize=True)
    lesson_screenshot().save(PLUGIN_ASSETS / "screenshot1.png", optimize=True)
    logo_mark().save(PLUGIN_ASSETS / "logo.png", optimize=True)
    logo_mark(dark=True).save(PLUGIN_ASSETS / "logo-dark.png", optimize=True)
    frames = [
        demo_frame(index).convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        for index in range(6)
    ]
    frames[0].save(
        DOC_ASSETS / "demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[1500, 1500, 1900, 1900, 1900, 2600],
        loop=0,
        optimize=True,
        disposal=2,
    )
    for path in [
        DOC_ASSETS / "social-preview.png",
        DOC_ASSETS / "demo.gif",
        PLUGIN_ASSETS / "logo.png",
        PLUGIN_ASSETS / "logo-dark.png",
        PLUGIN_ASSETS / "screenshot1.png",
    ]:
        print(f"generated {path}")


if __name__ == "__main__":
    main()

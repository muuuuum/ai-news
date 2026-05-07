#!/usr/bin/env python3
"""
YouTube AI News サムネイル生成スクリプト
AI News Daily ブランドガイドライン準拠

使い方:
  python3 generate_thumbnail.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

# === 設定 ===
WIDTH = 1280
HEIGHT = 720
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# カテゴリ別グラデーション色
GRADIENTS = {
    "security":  ((15, 23, 42),   (30, 27, 75)),    # ダークネイビー → ダークパープル
    "model":     ((30, 27, 75),   (49, 46, 129)),    # パープル系
    "business":  ((30, 58, 95),   (29, 78, 216)),    # ダークブルー
    "agent":     ((20, 83, 45),   (22, 101, 52)),    # ダークグリーン
    "startup":   ((19, 78, 74),   (13, 148, 136)),   # ティール
    "breaking":  ((127, 29, 29),  (220, 38, 38)),    # レッド
    "weekly":    ((15, 23, 42),   (30, 41, 59)),     # ダークネイビー
}

# ブランドカラー
ACCENT_RED = (220, 38, 38)
WHITE = (255, 255, 255)
WHITE_85 = (255, 255, 255, 217)  # 85% opacity


def create_gradient(width, height, color1, color2):
    """対角線グラデーション画像を生成"""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            t = (x / width * 0.6 + y / height * 0.4)
            r = int(color1[0] + (color2[0] - color1[0]) * t)
            g = int(color1[1] + (color2[1] - color1[1]) * t)
            b = int(color1[2] + (color2[2] - color1[2]) * t)
            pixels[x, y] = (r, g, b)
    return img


def get_font(size, bold=True):
    """フォントを取得（システムフォントにフォールバック）"""
    font_paths = [
        # macOS
        "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/Library/Fonts/NotoSansJP-Black.otf",
        "/Library/Fonts/NotoSansJP-Bold.otf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    if not bold:
        font_paths = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/Library/Fonts/NotoSansJP-Bold.otf",
            "/Library/Fonts/NotoSansJP-Regular.otf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_text_with_shadow(draw, pos, text, font, fill=WHITE, shadow_color=(0, 0, 0, 180), shadow_offset=3):
    """影付きテキスト描画"""
    x, y = pos
    # 影
    for dx in range(-shadow_offset, shadow_offset + 1):
        for dy in range(-shadow_offset, shadow_offset + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=shadow_color)
    # 本体
    draw.text(pos, text, font=font, fill=fill)


def draw_logo(draw, x, y):
    """AI News Daily ロゴを描画"""
    # 「AI」赤背景マーク
    logo_font = get_font(16)
    draw.rounded_rectangle([x, y, x + 32, y + 32], radius=5, fill=ACCENT_RED)
    draw.text((x + 5, y + 5), "AI", font=logo_font, fill=WHITE)

    # 「News Daily」
    name_font = get_font(18)
    draw.text((x + 40, y + 3), "News", font=name_font, fill=WHITE)
    draw.text((x + 92, y + 3), "Daily", font=name_font, fill=ACCENT_RED)


def draw_badge(draw, x, y, text, bg_color=ACCENT_RED, text_color=WHITE):
    """カテゴリバッジを描画"""
    badge_font = get_font(14, bold=True)
    bbox = draw.textbbox((0, 0), text, font=badge_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    padding_x = 12
    padding_y = 4
    draw.rounded_rectangle(
        [x, y, x + tw + padding_x * 2, y + th + padding_y * 2],
        radius=4,
        fill=bg_color
    )
    draw.text((x + padding_x, y + padding_y), text, font=badge_font, fill=text_color)
    return tw + padding_x * 2


def draw_number_badge(draw, x, y, number, label, highlight_color):
    """数字ハイライトバッジ"""
    num_font = get_font(32)
    label_font = get_font(13, bold=False)

    # 半透明背景
    draw.rounded_rectangle(
        [x, y, x + 140, y + 65],
        radius=8,
        fill=(255, 255, 255, 15)
    )

    draw_text_with_shadow(draw, (x + 10, y + 5), number, num_font, fill=highlight_color)
    draw.text((x + 10, y + 42), label, font=label_font, fill=(255, 255, 255, 180))


def generate_daily_thumbnail(
    main_text_lines,
    sub_text,
    category,
    numbers=None,
    date_text="",
    output_name="thumbnail_daily.png"
):
    """パターンA: Daily サムネイル生成"""
    colors = GRADIENTS.get(category, GRADIENTS["business"])
    img = create_gradient(WIDTH, HEIGHT, colors[0], colors[1])
    draw = ImageDraw.Draw(img, "RGBA")

    # ロゴ（左上）
    draw_logo(draw, 40, 40)

    # カテゴリバッジ
    cat_labels = {
        "security": "SECURITY",
        "model": "MODEL",
        "business": "BUSINESS",
        "agent": "AGENT",
        "startup": "STARTUP",
        "breaking": "BREAKING",
        "weekly": "WEEKLY",
    }
    draw_badge(draw, 40, 85, cat_labels.get(category, category.upper()))

    # メインテキスト（中央寄り）
    main_font = get_font(54)
    y_start = 200
    for i, line in enumerate(main_text_lines):
        highlight_color = {
            "security": (248, 113, 113),
            "model": (167, 139, 250),
            "business": (96, 165, 250),
            "agent": (52, 211, 153),
            "startup": (94, 234, 212),
        }.get(category, (248, 113, 113))

        draw_text_with_shadow(draw, (60, y_start + i * 70), line, main_font, fill=WHITE)

    # サブテキスト
    sub_font = get_font(28, bold=False)
    sub_y = y_start + len(main_text_lines) * 70 + 20
    sub_color = {
        "security": (248, 113, 113),
        "model": (167, 139, 250),
        "business": (96, 165, 250),
        "agent": (52, 211, 153),
        "startup": (94, 234, 212),
    }.get(category, (248, 113, 113))
    draw_text_with_shadow(draw, (60, sub_y), sub_text, sub_font, fill=sub_color, shadow_offset=2)

    # 数字バッジ
    if numbers:
        badge_y = 580
        for i, (num, label) in enumerate(numbers):
            highlight = {
                "security": (248, 113, 113),
                "model": (167, 139, 250),
                "business": (96, 165, 250),
                "agent": (52, 211, 153),
                "startup": (94, 234, 212),
            }.get(category, (248, 113, 113))
            draw_number_badge(draw, 60 + i * 160, badge_y, num, label, highlight)

    # 日付（右下、再生時間回避）
    if date_text:
        date_font = get_font(16, bold=False)
        draw.text((1080, 660), date_text, font=date_font, fill=(255, 255, 255, 150))

    output_path = os.path.join(OUTPUT_DIR, output_name)
    img.save(output_path, "PNG")
    print(f"生成完了: {output_path}")
    return output_path


def generate_breaking_thumbnail(
    main_text_lines,
    sub_text,
    output_name="thumbnail_breaking.png"
):
    """パターンD: Breaking サムネイル生成"""
    colors = GRADIENTS["breaking"]
    img = create_gradient(WIDTH, HEIGHT, colors[0], colors[1])
    draw = ImageDraw.Draw(img, "RGBA")

    # BREAKING バー（上部）
    draw.rectangle([0, 0, WIDTH, 50], fill=(180, 0, 0))
    bar_font = get_font(20)
    draw.text((40, 12), "BREAKING", font=bar_font, fill=WHITE)
    draw.text((180, 12), "BREAKING", font=bar_font, fill=WHITE)
    draw.text((320, 12), "BREAKING", font=bar_font, fill=WHITE)
    draw.text((460, 12), "BREAKING", font=bar_font, fill=WHITE)

    # ロゴ（左下）
    draw_logo(draw, 40, 620)

    # メインテキスト（中央）
    main_font = get_font(56)
    y_start = 220
    for i, line in enumerate(main_text_lines):
        draw_text_with_shadow(draw, (60, y_start + i * 75), line, main_font, fill=WHITE, shadow_offset=4)

    # サブテキスト
    sub_font = get_font(28, bold=False)
    sub_y = y_start + len(main_text_lines) * 75 + 30
    draw_text_with_shadow(draw, (60, sub_y), sub_text, sub_font, fill=(255, 200, 200), shadow_offset=2)

    # NOW バッジ
    draw_badge(draw, 1120, 620, "NOW", bg_color=(255, 255, 255), text_color=ACCENT_RED)

    output_path = os.path.join(OUTPUT_DIR, output_name)
    img.save(output_path, "PNG")
    print(f"生成完了: {output_path}")
    return output_path


# === サンプル生成 ===
if __name__ == "__main__":
    # サンプル 1: Daily — Claude Code 流出ニュース
    generate_daily_thumbnail(
        main_text_lines=["50万行 流出", "Claude Code"],
        sub_text="未公開44機能が判明 / Anthropic",
        category="security",
        numbers=[
            ("512,000", "行のコード"),
            ("1,900", "ファイル"),
            ("44", "未公開機能"),
        ],
        date_text="2026.4.3",
        output_name="thumbnail_claude_code_leak.png",
    )

    # サンプル 2: Daily — GPT-5.4 コンピュータ操作
    generate_daily_thumbnail(
        main_text_lines=["GPT-5.4 Thinking", "PC操作を初搭載"],
        sub_text="OSWorld 記録更新 / GDPVal 83.0%",
        category="model",
        numbers=[
            ("83.0%", "GDPVal"),
            ("1位", "OSWorld"),
        ],
        date_text="2026.4.3",
        output_name="thumbnail_gpt54_thinking.png",
    )

    # サンプル 3: Breaking — Claude Code 流出（速報版）
    generate_breaking_thumbnail(
        main_text_lines=["【速報】Claude Code", "ソースコード流出"],
        sub_text="512,000行 / 44個の未公開機能が判明",
        output_name="thumbnail_breaking_claude_code.png",
    )

    print("\n全サムネイル生成完了!")

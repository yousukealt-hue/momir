import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import random

# ============================
# 設定
# ============================
WIDTH = 300
HEIGHT = 400
FONT_PATH = r"C:\Windows\Fonts\DejaVuSans.ttc"
MARGIN = 12
HEADERS = {"User-Agent": "MomirPrinter/1.0"}

# ============================
# ここにあなたの関数群を全部コピペ
# draw_card_name_and_cost
# draw_type_line
# wrap_by_pixel
# draw_text_block
# crop_art_from_card
# to_monochrome
# fetch_random_creature_by_cmc
# fetch_japanese_or_english_print

# ============================
# 名前＋マナコスト
# ============================

def draw_card_name_and_cost(draw, y, name, mana_cost, max_height=36):
    start_y = y

    size = 32
    MIN_SIZE = 12

    while True:
        font_name = ImageFont.truetype(FONT_PATH, size)
        font_cost = ImageFont.truetype(FONT_PATH, max(size - 6, 10))

        # 幅チェック
        name_ok = draw.textlength(name, font=font_name) <= (WIDTH - MARGIN*2)

        if mana_cost:
            bbox = draw.textbbox((0, 0), mana_cost, font=font_cost)
            cost_width = bbox[2] - bbox[0]
            cost_ok = cost_width <= (WIDTH - MARGIN*2)
        else:
            cost_ok = True

        # 高さチェック
        total_height = font_name.size + 2 + font_name.size + 2
        height_ok = total_height <= max_height

        if name_ok and cost_ok and height_ok:
            break

        size -= 2
        if size < MIN_SIZE:
            size = MIN_SIZE
            font_name = ImageFont.truetype(FONT_PATH, size)
            font_cost = ImageFont.truetype(FONT_PATH, max(size - 6, 10))
            break

    # 描画
    draw.text((MARGIN, y), name, font=font_name, fill=0)
    y += font_name.size + 2

    if mana_cost:
        bbox = draw.textbbox((0, 0), mana_cost, font=font_cost)
        w_cost = bbox[2] - bbox[0]
        draw.text((WIDTH - MARGIN - w_cost, y), mana_cost, font=font_cost, fill=0)

    y += font_name.size + 4

    # 高さ制限（強制）
    if y - start_y > max_height:
        y = start_y + max_height

    return y



# ============================
# タイプ行
# ============================
def draw_type_line(draw, x, y, type_line, max_width=300 - 24, max_height=20):
    size = 14
    MIN_SIZE = 10

    while True:
        font_type = ImageFont.truetype(FONT_PATH, size)
        if draw.textlength(type_line, font=font_type) <= max_width:
            break
        size -= 2
        if size < MIN_SIZE:
            size = MIN_SIZE
            font_type = ImageFont.truetype(FONT_PATH, size)
            break

    draw.text((x, y), type_line, font=font_type, fill=0)
    return y + font_type.size + 6


# ============================
# wrap
# ============================
def wrap_by_pixel(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            test = current + char
            if draw.textlength(test, font=font) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


# ============================
# 能力テキスト（完全自動縮小）
# ============================

def draw_text_block(draw, x, y, text, font, max_width, max_height, line_spacing=1):
    size = font.size
    MIN_SIZE = 10

    # 1px ずつ下げて最適サイズを探す
    while size >= MIN_SIZE:
        test_font = ImageFont.truetype(FONT_PATH, size)
        lines = wrap_by_pixel(draw, text, test_font, max_width)

        total_height = len(lines) * (test_font.size + line_spacing)
        too_wide = any(draw.textlength(line, font=test_font) > max_width for line in lines)

        if not too_wide and total_height <= max_height:
            break

        size -= 1

    # 描画
    test_font = ImageFont.truetype(FONT_PATH, size)
    lines = wrap_by_pixel(draw, text, test_font, max_width)

    for line in lines:
        draw.text((x, y), line, font=test_font, fill=0)
        y += test_font.size + line_spacing

    return y



# ============================
# アート切り抜き
# ============================
def crop_art_from_card(image):
    w, h = image.size
    top = int(h * 0.12)+10
    bottom = int(h * 0.52)+10
    return image.crop((0, top, w, bottom))


# ============================
# 白黒化
# ============================
def to_monochrome(img):
    return img.convert("L").convert("1")


# ============================
# Scryfall 抽選
# ============================
def fetch_random_creature_by_cmc(cmc: int):
    url = "https://api.scryfall.com/cards/random"
    params = {"q": f"type:creature cmc={cmc} -is:digital"}
    r = requests.get(url, params=params, headers=HEADERS)
    return r.json()


def fetch_japanese_or_english_print(card):
    set_code = card["set"]
    cn = card["collector_number"]
    url_ja = f"https://api.scryfall.com/cards/{set_code}/{cn}/ja"
    url_en = f"https://api.scryfall.com/cards/{set_code}/{cn}"

    r = requests.get(url_ja, headers=HEADERS)
    if r.status_code == 200:
        return r.json(), True
    return requests.get(url_en, headers=HEADERS).json(), False


# ============================

def generate_card_image(cmc):
    base_card = fetch_random_creature_by_cmc(cmc)
    card, is_japanese = fetch_japanese_or_english_print(base_card)

    name = card.get("printed_name") or card.get("name")
    type_line = card.get("printed_type_line") or card.get("type_line")
    oracle = card.get("printed_text") or card.get("oracle_text") or ""
    p = card.get("power", "?")
    t = card.get("toughness", "?")

    # --- カード画像取得 ---
    img_url = card["image_uris"]["normal"]
    img_data = requests.get(img_url, headers=HEADERS).content
    card_img = Image.open(io.BytesIO(img_data))

    # --- アート切り抜き ---
    art = crop_art_from_card(card_img)
    w, h = art.size
    scale = WIDTH / w
    art = art.resize((WIDTH, int(h * scale)), Image.LANCZOS)
    art = to_monochrome(art)

    # --- ベースキャンバス ---
    base = Image.new("1", (WIDTH, HEIGHT), 1)
    base.paste(art, (0, 0))

    draw = ImageDraw.Draw(base)
    y = art.height + 2

    # --- 名前＋マナコスト ---
    mana_cost = card.get("mana_cost", "")
    y = draw_card_name_and_cost(draw, y, name, mana_cost)

    # --- タイプ行 ---
    y = draw_type_line(draw, MARGIN, y, type_line)

    # ============================
    # ここからが重要：能力欄の高さを動的に決定
    # ============================

    # P/T のフォント（高さを知るため）
    font_pt = ImageFont.truetype(FONT_PATH, 18)
    pt_text = f"{p}/{t}"
    bbox = draw.textbbox((0, 0), pt_text, font=font_pt)
    h_pt = bbox[3] - bbox[1]

    # P/T のために確保する領域（20px + P/T の高さ）
    pt_reserved = 20 + h_pt

    # 現在位置 y から見た残り高さ
    remaining_height = HEIGHT - y - pt_reserved

    # 安全のため最低 20px は確保
    if remaining_height < 20:
        remaining_height = 20

    # --- 能力欄（残り高さを最大限使う） ---
    font_rules = ImageFont.truetype(FONT_PATH, 14)
    y = draw_text_block(
        draw,
        MARGIN,
        y,
        oracle,
        font_rules,
        max_width=WIDTH - MARGIN*2,
        max_height=remaining_height
    )

    # --- P/T（右下固定） ---
    bbox = draw.textbbox((0, 0), pt_text, font=font_pt)
    w_pt = bbox[2] - bbox[0]
    h_pt = bbox[3] - bbox[1]

    pt_y = HEIGHT - 10 - h_pt
    draw.text((WIDTH - MARGIN - w_pt, pt_y), pt_text, font=font_pt, fill=0)

    return base



# ============================
# Streamlit UI
# ============================
st.title("Momir Web Printer (EZSign Edition)")
st.write("CMC を選んでカードを生成しよう")

# 履歴初期化
if "history" not in st.session_state:
    st.session_state.history = []

cmc = st.number_input("CMC", min_value=0, max_value=20, value=3)

# 大きいボタン（iPhone向け）
if st.button("カード生成", use_container_width=True):
    img = generate_card_image(cmc)
    st.image(img, caption="生成されたカード", width=300)


    # ダウンロード用データ
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()

    st.download_button(
        label="画像を保存（iPhone用）",
        data=byte_im,
        file_name="momir_card.png",
        mime="image/png",
        use_container_width=True
    )

    # 履歴に追加（最大5枚）
    st.session_state.history.append(img)
    st.session_state.history = st.session_state.history[-5:]

# ============================
# 生成履歴（横並び）
# ============================
if st.session_state.history:
    st.write("### 生成履歴（最新5枚）")

    cols = st.columns(len(st.session_state.history))

    for col, hist_img in zip(cols, st.session_state.history):
        with col:
            st.image(hist_img, width=300)



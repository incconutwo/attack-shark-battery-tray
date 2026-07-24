from typing import Tuple, Dict
from PIL import Image, ImageDraw, ImageFont
from config import is_light_mode

_FONT_CACHE = {}


def get_font(size: int):
    """Reuse loaded ImageFont handles to avoid repeated disk reads and RAM allocations."""
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.truetype("arialbd.ttf", size)
        except OSError:
            try:
                _FONT_CACHE[size] = ImageFont.truetype("arial.ttf", size)
            except OSError:
                _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def create_image(text: str, text_color: Tuple[int, int, int], icon_cache: Dict) -> Image.Image:
    cache_key = (text, text_color)
    if cache_key in icon_cache:
        return icon_cache[cache_key]

    width, height = 64, 64
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    font = get_font(54 if len(text) <= 2 else 34)
        
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    
    x = (width - text_width) / 2 - left
    y = (height - text_height) / 2 - top
        
    draw.text((x, y), text, fill=text_color, font=font)

    if len(icon_cache) > 30:
        icon_cache.clear()
    icon_cache[cache_key] = image
    return image


def get_icon_data(status: str, last_battery: int, icon_cache: Dict) -> Image.Image:
    light = is_light_mode()
    if status == "disconnected":
        color = (70, 70, 70) if light else (170, 170, 170)
        return create_image("??", color, icon_cache)
    elif status == "connected" and last_battery < 0:
        color = (70, 70, 70) if light else (170, 170, 170)
        return create_image("--", color, icon_cache)
    elif status == "charging" and last_battery < 0:
        color = (21, 101, 192) if light else (52, 152, 219)
        return create_image("Chg", color, icon_cache)
    elif status == "unknown":
        color = (142, 68, 173) if light else (155, 89, 182)
        return create_image("?", color, icon_cache)
    else:
        pct = last_battery
        if status == "charging":
            color = (21, 101, 192) if light else (52, 152, 219)
        elif pct >= 50:
            color = (30, 140, 60) if light else (46, 204, 113)
        elif pct >= 20:
            color = (211, 84, 0) if light else (230, 126, 34)
        else:
            color = (192, 57, 43) if light else (231, 76, 60)
        return create_image(str(pct), color, icon_cache)

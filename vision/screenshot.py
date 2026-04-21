"""
Screenshot capture — always returns an image in LOGICAL pixel coordinates.

Uses PIL.ImageGrab(all_screens=False) which captures only the primary screen
at the DPI-virtualised resolution — the same coordinate space pyautogui.click()
uses.  No DPI mismatch possible.

Annotations:
  • Rulers on all FOUR edges (top, left, right, bottom) with labels every 100 px
  • Faint red grid every 100 px across the image
  • Large "x,y" labels at every 100 px intersection in the content area
"""
import io
import base64
import pyautogui
from PIL import Image, ImageDraw, ImageFont, ImageGrab


# ── fonts ─────────────────────────────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.ImageFont:
    for path in [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


_FONT_RULER = _load_font(10)
_FONT_GRID  = _load_font(10)


# ── capture ───────────────────────────────────────────────────────────────────

def capture() -> tuple[Image.Image, int, int]:
    """
    Capture the primary screen at logical (click-space) resolution.
    ImageGrab(all_screens=False) → primary monitor only, logical coords.
    """
    logical_w, logical_h = pyautogui.size()
    try:
        img = ImageGrab.grab(all_screens=False)
    except Exception:
        img = pyautogui.screenshot()
    if img.size != (logical_w, logical_h):
        img = img.resize((logical_w, logical_h), Image.LANCZOS)
    return img, logical_w, logical_h


def capture_base64(annotate: bool = True) -> tuple[str, int, int]:
    img, w, h = capture()
    if annotate:
        img = _annotate(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return data, w, h


# ── annotation ────────────────────────────────────────────────────────────────

_R = 20   # ruler strip thickness (px) — kept thin so little content is hidden


def _annotate(img: Image.Image) -> Image.Image:
    img = _add_grid(img)
    img = _add_rulers(img)
    return img


def _add_grid(img: Image.Image) -> Image.Image:
    """
    Faint grid every 100 px + coordinate labels at every 100 px intersection.
    Labels use an opaque background so they're readable over any content.
    IMPORTANT: labels show the EXACT logical pixel coordinate to pass to click().
    """
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    GRID  = (220, 60, 60, 20)     # very faint red lines
    FG    = (255, 210, 210, 245)  # label text
    BG    = (  0,   0,   0, 170) # label background

    # Grid lines (skip ruler strip)
    for x in range(100, w, 100):
        draw.line([(x, _R), (x, h - _R)], fill=GRID, width=1)
    for y in range(100, h, 100):
        draw.line([(_R, y), (w - _R, y)], fill=GRID, width=1)

    # Labels at every 100 px intersection — smaller text, more of them
    for x in range(100, w, 100):
        for y in range(100, h, 100):
            label = f"{x},{y}"
            bbox  = draw.textbbox((x + 2, y + 2), label, font=_FONT_GRID)
            pad   = 1
            draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad], fill=BG)
            draw.text((x + 2, y + 2), label, fill=FG, font=_FONT_GRID)

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _add_rulers(img: Image.Image) -> Image.Image:
    """
    Ruler strips on ALL FOUR edges so Y can be read on left OR right,
    and X can be read on top OR bottom.  Labels every 100 px.
    """
    w, h = img.size
    draw = ImageDraw.Draw(img)

    R     = _R
    BG    = (18,  18,  20)
    TICK  = (255,  80,  80)
    LABEL = (255, 160, 160)

    # ── backgrounds ──────────────────────────────────────────────────────────
    draw.rectangle([(0,   0),   (w,   R)], fill=BG)   # top
    draw.rectangle([(0,   h-R), (w,   h)], fill=BG)   # bottom
    draw.rectangle([(0,   0),   (R,   h)], fill=BG)   # left
    draw.rectangle([(w-R, 0),   (w,   h)], fill=BG)   # right
    # corners
    for cx, cy in [(0,0),(w-R,0),(0,h-R),(w-R,h-R)]:
        draw.rectangle([(cx, cy), (cx+R, cy+R)], fill=(10,10,12))

    # ── top + bottom: X axis ─────────────────────────────────────────────────
    for x in range(0, w, 50):
        major = (x % 100 == 0)
        th    = R if major else R // 2
        # top ticks (pointing down)
        draw.line([(x, R-th), (x, R)], fill=TICK, width=1)
        # bottom ticks (pointing up)
        draw.line([(x, h-R), (x, h-R+th)], fill=TICK, width=1)
        if major and 0 < x < w - R:
            draw.text((x+2,  2),   str(x), fill=LABEL, font=_FONT_RULER)  # top
            draw.text((x+2,  h-R+2), str(x), fill=LABEL, font=_FONT_RULER)  # bottom

    # ── left + right: Y axis ─────────────────────────────────────────────────
    for y in range(0, h, 50):
        major = (y % 100 == 0)
        tw    = R if major else R // 2
        # left ticks (pointing right)
        draw.line([(R-tw, y), (R, y)], fill=TICK, width=1)
        # right ticks (pointing left)
        draw.line([(w-R, y), (w-R+tw, y)], fill=TICK, width=1)
        if major and 0 < y < h - R:
            draw.text((2,   y+2), str(y), fill=LABEL, font=_FONT_RULER)   # left
            draw.text((w-R+2, y+2), str(y), fill=LABEL, font=_FONT_RULER) # right

    return img

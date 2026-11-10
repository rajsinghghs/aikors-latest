"""Shrink product preview images so the store page stays small and fast."""
import io


def preview_variants(content: bytes):
    """Return (full_jpeg, thumb_jpeg, content_type). Falls back to the original bytes."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return content, content, None

    image = Image.open(io.BytesIO(content))
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGB":
        image = image.convert("RGB")
    full = _jpeg(_fit(image, 1280), 80)
    thumb = _jpeg(_fit(image, 420), 68)
    return full, thumb, "image/jpeg"


def _fit(image, edge: int):
    copy = image.copy()
    copy.thumbnail((edge, edge))
    return copy


def _jpeg(image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()

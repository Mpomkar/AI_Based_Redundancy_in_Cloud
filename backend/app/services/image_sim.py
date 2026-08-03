from io import BytesIO

import imagehash
from PIL import Image

from app.config import settings


def phash_hex(data: bytes) -> str:
    img = Image.open(BytesIO(data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    h = imagehash.phash(img, hash_size=settings.image_hash_size)
    return str(h)


def phash_similarity(hex_a: str, hex_b: str) -> float:
    ha = imagehash.hex_to_hash(hex_a)
    hb = imagehash.hex_to_hash(hex_b)
    bits = float(settings.image_hash_size**2)
    dist = float(ha - hb)
    return max(0.0, 1.0 - (dist / bits))

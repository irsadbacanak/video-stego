"""LSB (Least Significant Bit) steganography — Kişi 2"""

import numpy as np
import cv2

DEFAULT_KEY = 42


# ══════════════════════════════════════════════
# 1. YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════

def bytes_to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        bits.extend([int(x) for x in format(byte, "08b")])
    return bits

def bits_to_bytes(bits: list) -> bytes:
    result = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        result.append(int("".join(str(b) for b in byte), 2))
    return bytes(result)


# ══════════════════════════════════════════════
# 2. HEADER
# [1 byte tip][4 byte boyut][veri]
# tip: 0 = metin, 1 = resim
# ══════════════════════════════════════════════

def build_payload(data: bytes, payload_type: int) -> list:
    header = bytes([payload_type]) + len(data).to_bytes(4, "big")
    return bytes_to_bits(header + data)

def parse_payload(bits: list):
    raw = bits_to_bytes(bits)
    payload_type = raw[0]
    size = int.from_bytes(raw[1:5], "big")
    data = raw[5:5 + size]
    return payload_type, data


# ══════════════════════════════════════════════
# 3. KAPASİTE
# ══════════════════════════════════════════════

def calculate_capacity(frame: np.ndarray) -> int:
    """Bir kareye kaç byte payload sığar?"""
    h, w, c = frame.shape
    return (h * w * c - 40) // 8


# ══════════════════════════════════════════════
# 4. EMBED
# ══════════════════════════════════════════════

def _pixel_indices(total: int, n: int, key: int) -> np.ndarray:
    """Anahtar ile belirlenmiş, tekrarlanabilir rastgele piksel indeksleri üretir."""
    return np.random.default_rng(key).permutation(total)[:n]


def _embed_bits(frame: np.ndarray, bits: list, key: int = DEFAULT_KEY) -> np.ndarray:
    n = len(bits)
    stego = np.array(frame, copy=True, dtype=np.uint8)
    flat = stego.ravel()
    idx = _pixel_indices(len(flat), n, key)
    flat[idx] = (flat[idx] & 0xFE) | np.asarray(bits, dtype=np.uint8)
    return stego


def embed(frame: np.ndarray, message: str, key: int = DEFAULT_KEY) -> np.ndarray:
    """Metni kareye gömer."""
    data = message.encode("utf-8")
    if len(data) > calculate_capacity(frame):
        raise ValueError(f"Mesaj çok uzun! Max {calculate_capacity(frame)} byte.")
    return _embed_bits(frame, build_payload(data, payload_type=0), key)


def embed_image(frame: np.ndarray, image_path: str, key: int = DEFAULT_KEY) -> np.ndarray:
    """Resim dosyasını kareye gömer."""
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > calculate_capacity(frame):
        raise ValueError(f"Resim çok büyük! Max {calculate_capacity(frame)} byte.")
    return _embed_bits(frame, build_payload(data, payload_type=1), key)


# ══════════════════════════════════════════════
# 5. EXTRACT
# ══════════════════════════════════════════════

def extract(frame: np.ndarray, key: int = DEFAULT_KEY):
    """
    Kareden payload çıkarır.
    Döner: ("text", "mesaj metni")
        veya ("image", b"...bytes...")
    """
    try:
        flat = frame.ravel()
        total = len(flat)
        # Gömme ile aynı anahtar kullanılarak indeksler yeniden üretilir
        all_idx = np.random.default_rng(key).permutation(total)

        header_count = 40  # 1 tip + 4 boyut byte = 5 byte = 40 bit
        header_raw = bits_to_bytes((flat[all_idx[:header_count]] & 1).astype(np.uint8).tolist())
        size = int.from_bytes(header_raw[1:5], "big")
        total_bits = (5 + size) * 8

        if total_bits > total:
            raise ValueError("Geçersiz payload boyutu")

        payload_bits = (flat[all_idx[:total_bits]] & 1).astype(np.uint8).tolist()
        payload_type, data = parse_payload(payload_bits)
        if payload_type == 0:
            return "text", data.decode("utf-8")
        else:
            return "image", data
    except Exception as e:
        raise ValueError(f"Kareden veri çıkarılamadı: {e}")


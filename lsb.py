"""LSB (Least Significant Bit) steganography — Kişi 2"""

import numpy as np
import cv2


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

def embed(frame: np.ndarray, message: str) -> np.ndarray:
    """Metni kareye gömer."""
    data = message.encode("utf-8")
    if len(data) > calculate_capacity(frame):
        raise ValueError(f"Mesaj çok uzun! Max {calculate_capacity(frame)} byte.")
    bits = build_payload(data, payload_type=0)
    stego = frame.copy().astype(np.uint8)
    flat = stego.flatten()
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit
    return flat.reshape(frame.shape)

def embed_image(frame: np.ndarray, image_path: str) -> np.ndarray:
    """Resmi kareye gömer."""
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > calculate_capacity(frame):
        raise ValueError(f"Resim çok büyük! Max {calculate_capacity(frame)} byte.")
    bits = build_payload(data, payload_type=1)
    stego = frame.copy().astype(np.uint8)
    flat = stego.flatten()
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit
    return flat.reshape(frame.shape)


# ══════════════════════════════════════════════
# 5. EXTRACT
# ══════════════════════════════════════════════

def extract(frame: np.ndarray):
    """
    Kareden payload çıkarır.
    Döner: ("text", "mesaj metni")
        veya ("image", b"...png bytes...")
    """
    try:
        flat = frame.flatten()
        bits = [int(p) & 1 for p in flat]
        payload_type, data = parse_payload(bits)
        if payload_type == 0:
            return "text", data.decode("utf-8")
        else:
            return "image", data
    except Exception as e:
        raise ValueError(f"Kareden veri çıkarılamadı: {e}")

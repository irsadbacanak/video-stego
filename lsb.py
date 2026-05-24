"""LSB (Least Significant Bit) steganography """

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
# 2. HEADER — tip + boyut bilgisi saklar
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
    return (h * w * c - 40) // 8  # 5 byte header düş


# ══════════════════════════════════════════════
# 4. EMBED — Kişi 1'in verdiği kareye gömer
# ══════════════════════════════════════════════

def embed(frame: np.ndarray, message: str) -> np.ndarray:
    """Metni kareye gömer. Kişi 1'in döngüsünde her kare için çağrılır."""
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
    """Resmi kareye gömer. Kişi 1'in döngüsünde her kare için çağrılır."""
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
# 5. EXTRACT — Kareden payload çıkarır
# ══════════════════════════════════════════════

def extract(frame: np.ndarray):
    """
    Kareden payload çıkarır.
    Döner: ("text", "mesaj metni")
        veya ("image", b"...png bytes...")
    """
    flat = frame.flatten()
    bits = [int(p) & 1 for p in flat]
    payload_type, data = parse_payload(bits)
    if payload_type == 0:
        return "text", data.decode("utf-8")
    else:
        return "image", data

# ══════════════════════════════════════════════
# 6. BAŞARI METRİKLERİ
# ══════════════════════════════════════════════

from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

def calculate_psnr(original: np.ndarray, stego: np.ndarray) -> float:
    """
    PSNR hesaplar. Yüksek = iyi.
    40 dB üzeri → gözle fark edilmez.
    """
    return psnr(original, stego, data_range=255)

def calculate_ssim(original: np.ndarray, stego: np.ndarray) -> float:
    """
    SSIM hesaplar. 1'e yakın = iyi.
    0.99+ → görsel kalite korunmuş.
    """
    return ssim(original, stego, channel_axis=2, data_range=255)

def calculate_ber(original_message: str, extracted_message: str) -> float:
    """
    Bit Hata Oranı (BER).
    0.0 → veri kayıpsız iletildi.
    """
    orig_bits = bytes_to_bits(original_message.encode("utf-8"))
    extr_bits = bytes_to_bits(extracted_message.encode("utf-8"))
    
    min_len = min(len(orig_bits), len(extr_bits))
    if min_len == 0:
        return 1.0
    
    hatalar = sum(o != e for o, e in zip(orig_bits[:min_len], extr_bits[:min_len]))
    return hatalar / min_len

def evaluate(original: np.ndarray, stego: np.ndarray, message: str) -> dict:
    """
    Tek fonksiyonla tüm metrikleri hesaplar.
    Kullanım: results = evaluate(frame, stego_frame, "mesaj")
    """
    _, extracted = extract(stego)
    
    results = {
        "PSNR (dB)"  : calculate_psnr(original, stego),
        "SSIM"       : calculate_ssim(original, stego),
        "BER"        : calculate_ber(message, extracted),
        "Kapasite"   : calculate_capacity(original),
        "Mesaj boyutu (byte)": len(message.encode("utf-8")),
        "Doluluk (%)" : len(message.encode("utf-8")) / calculate_capacity(original) * 100,
    }
    
    print("=" * 35)
    print("      LSB STEGANOGRAFİ METRİKLERİ")
    print("=" * 35)
    for k, v in results.items():
        if isinstance(v, float):
            print(f"  {k:<22}: {v:.4f}")
        else:
            print(f"  {k:<22}: {v}")
    print("=" * 35)
    
    return results

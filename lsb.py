"""LSB (Least Significant Bit) steganography """

import numpy as np

def text_to_bits(text: str) -> list:
    """Metni bit listesine çevirir. Sonu NULL (8 sıfır) ile işaretlenir."""
    bits = []
    for char in text:
        b = format(ord(char), "08b")
        bits.extend([int(x) for x in b])
    bits.extend([0] * 8)  # NULL terminator
    return bits


def bits_to_text(bits: list) -> str:
    """Bit listesini metne çevirir. NULL byte'ta durur."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        val = int("".join(str(b) for b in byte), 2)
        if val == 0:  # NULL terminator
            break
        chars.append(chr(val))
    return "".join(chars)


def calculate_capacity(frame: np.ndarray) -> int:
    """Bir kareye kaç karakter sığar?"""
    h, w, c = frame.shape
    total_bits = h * w * c  # her piksel kanalına 1 bit
    return (total_bits - 8) // 8


def embed(frame: np.ndarray, message: str) -> np.ndarray:
    """Mesajı frame'e gömer, stego frame döner."""
    bits = text_to_bits(message)
    capacity = calculate_capacity(frame)

    if len(message) > capacity:
        raise ValueError(f"Mesaj çok uzun! Max {capacity} karakter.")

    stego = frame.copy().astype(np.uint8)
    flat = stego.flatten()

    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit  # son biti değiştir

    return flat.reshape(frame.shape)


def extract(frame: np.ndarray) -> str:
    """Stego frame'den mesajı çıkarır."""
    flat = frame.flatten()
    bits = [int(p) & 1 for p in flat]  # her pikselin son biti
    return bits_to_text(bits)

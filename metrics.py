"""Image quality and accuracy metrics — Kişi 4"""

import numpy as np
from skimage.metrics import peak_signal_noise_ratio as skimage_psnr
from skimage.metrics import structural_similarity as skimage_ssim

def psnr(original: np.ndarray, stego: np.ndarray) -> float:
    """Orijinal ve stego kare arasındaki PSNR değerini hesaplar (>35dB genelde iyidir)."""
    return skimage_psnr(original, stego, data_range=255)

def ssim(original: np.ndarray, stego: np.ndarray) -> float:
    """Orijinal ve stego kare arasındaki SSIM değerini hesaplar (1'e yaklaştıkça iyidir)."""
    return skimage_ssim(original, stego, channel_axis=-1, data_range=255)

def ber(original_msg: bytes, extracted_msg: bytes) -> float:
    """Orijinal mesaj ile çıkarılan mesaj arasındaki Bit Hata Oranını (BER) hesaplar."""
    orig_bits = "".join(format(byte, "08b") for byte in original_msg)
    ext_bits = "".join(format(byte, "08b") for byte in extracted_msg)
    
    min_len = min(len(orig_bits), len(ext_bits))
    errors = sum(1 for i in range(min_len) if orig_bits[i] != ext_bits[i])
    
    errors += abs(len(orig_bits) - len(ext_bits))
    total_bits = max(len(orig_bits), len(ext_bits))
    
    return errors / total_bits if total_bits > 0 else 0.0

def rs_analysis(stego: np.ndarray) -> float:
    
    
    if len(stego.shape) == 3:
        channel = stego[:, :, 0].astype(np.int16)
    else:
        channel = stego.astype(np.int16)

    
    h, w = channel.shape
    h -= h % 2
    w -= w % 2
    channel = channel[:h, :w]

    
    def discrimination(img):
        return np.sum(np.abs(img[:, :-1] - img[:, 1:]))

    
    def flip_lsb(img):
        return img ^ 1

    d_original = discrimination(channel)
    d_flipped = discrimination(flip_lsb(channel))

    
    ratio = d_original / (d_flipped + 1e-5)
    
    z
    risk_score = max(0.0, min(1.0, (ratio - 0.85) * 6.66)) 
    return risk_score
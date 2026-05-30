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

def _rs_channel(channel: np.ndarray) -> float:
    """Tek kanalda Fridrich RS analizi uygular."""
    img = channel.astype(np.int16)
    h, w = img.shape
    w4 = (w // 4) * 4
    if w4 < 4:
        return 0.0

    # 4'lü yatay piksel grupları
    groups = img[:, :w4].reshape(-1, 4)

    # Maske: 2. ve 3. pozisyonlardaki pikseller işleme alınır
    mask = np.array([False, False, True, True])

    def f(g):
        return np.sum(np.abs(np.diff(g, axis=1)), axis=1)

    def F_pos(g):
        # Pozitif flip: LSB ^ 1 (0↔1, 2↔3, ...)
        r = g.copy()
        r[:, mask] ^= 1
        return r

    def F_neg(g):
        # Negatif flip: 2k ↔ 2k-1  (çift→-1, tek→+1)
        r = g.copy()
        x = r[:, mask]
        r[:, mask] = np.where(x % 2 == 0, x - 1, x + 1)
        return r

    d0 = f(groups)
    dp = f(F_pos(groups))
    dn = f(F_neg(groups))

    R_m  = np.sum(dp > d0)
    S_m  = np.sum(dp < d0)
    R_nm = np.sum(dn > d0)
    S_nm = np.sum(dn < d0)

    total = len(groups)
    # Temiz görüntüde ≈0; LSB gömme arttıkça pozitife kayar
    # Gömme R_m'yi düşürür, R_nm'yi yükseltir → fark negatif → işareti çevir
    rs = ((R_nm - S_nm) - (R_m - S_m)) / total
    return float(max(0.0, min(1.0, rs * 2.0)))


def rs_analysis(stego: np.ndarray) -> float:
    if stego.ndim == 3:
        scores = [_rs_channel(stego[:, :, c]) for c in range(stego.shape[2])]
        return float(np.mean(scores))
    return _rs_channel(stego)
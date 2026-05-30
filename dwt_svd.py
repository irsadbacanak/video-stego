"""DWT-SVD watermarking — Kişi 3"""

from __future__ import annotations

import numpy as np
import cv2
import pywt

from video_io import split_ycbcr, merge_ycbcr

WAVELET = "haar"


def _to_grayscale(watermark: np.ndarray | str) -> np.ndarray:
    if isinstance(watermark, str):
        img = cv2.imread(watermark, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Watermark okunamadı: {watermark}")
        return img
    if watermark.ndim == 3:
        return cv2.cvtColor(watermark, cv2.COLOR_BGR2GRAY)
    return watermark.astype(np.uint8)


def _dwt_decompose(channel: np.ndarray) -> tuple[np.ndarray, tuple]:
    coeffs = pywt.dwt2(channel.astype(np.float64), WAVELET)
    return coeffs[0], coeffs[1]


def _dwt_reconstruct(ll: np.ndarray, details: tuple) -> np.ndarray:
    return pywt.idwt2((ll, details), WAVELET)


def _svd(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u, s, vt = np.linalg.svd(matrix, full_matrices=False)
    return u, s, vt


def _reconstruct_from_svd(u: np.ndarray, s: np.ndarray, vt: np.ndarray) -> np.ndarray:
    return u @ np.diag(s) @ vt


def embed(frame: np.ndarray, watermark: np.ndarray | str, alpha: float = 0.1) -> np.ndarray:
    """
    Watermark'ı Y kanalının LL alt bandına DWT-SVD ile gömer.

    Akış: BGR → Y → DWT(LL) → SVD(watermark) → LL' = LL + α·U_w Σ_w V_w^T → IDWT → BGR
    """
    if not 0 < alpha <= 1:
        raise ValueError("alpha (0, 1] aralığında olmalı")

    y, cb, cr = split_ycbcr(frame)
    ll, details = _dwt_decompose(y)

    w = _to_grayscale(watermark)
    w_resized = cv2.resize(
        w, (ll.shape[1], ll.shape[0]), interpolation=cv2.INTER_AREA
    ).astype(np.float64)

    uw, sw, vtw = _svd(w_resized)
    w_svd = _reconstruct_from_svd(uw, sw, vtw)

    w_max = np.abs(w_svd).max()
    if w_max > 1e-8:
        w_svd = w_svd / w_max  # [-1, 1]
    ll_new = ll + alpha * 200.0 * w_svd
    y_new = _dwt_reconstruct(ll_new, details)
    y_new = np.clip(y_new, 0, 255).astype(np.uint8)

    return merge_ycbcr(y_new, cb, cr)


def extract(
    frame: np.ndarray, original: np.ndarray, alpha: float = 0.1
) -> np.ndarray:
    """
    Non-blind çıkarma: orijinal ve stego karelerin LL farkından watermark kurtarır.

    Döner: gri watermark (float64, LL boyutunda).
    """
    if not 0 < alpha <= 1:
        raise ValueError("alpha (0, 1] aralığında olmalı")

    y_orig, _, _ = split_ycbcr(original)
    y_stego, _, _ = split_ycbcr(frame)

    ll_orig, _ = _dwt_decompose(y_orig)
    ll_stego, _ = _dwt_decompose(y_stego)

    # alpha * 200.0 ile böl — embed'deki ölçeklemeyi tam tersine çevirir
    w_rec = (ll_stego - ll_orig) / (alpha * 200.0)
    return np.clip(w_rec, 0, 255).astype(np.float64)


def normalized_correlation(
    watermark: np.ndarray | str, recovered: np.ndarray
) -> float:
    """
    Standart NC: Σ(W · W_rec) / sqrt(Σ(W²) · Σ(W_rec²))

    Önceki Pearson formülü ortalamayı çıkarıyordu ve ölçek/offset
    hatalarına kördu (her zaman ~1.0 veriyordu). Bu formül gerçek
    benzerliği ölçer; bozulan ya da yanlış watermark'ta NC düşer.
    """
    w = _to_grayscale(watermark).astype(np.float64)
    r = recovered.astype(np.float64)
    r_resized = cv2.resize(r, (w.shape[1], w.shape[0]), interpolation=cv2.INTER_AREA)
    num = np.sum(w * r_resized)
    denom = np.sqrt(np.sum(w ** 2) * np.sum(r_resized ** 2))
    if denom < 1e-10:
        return 0.0
    return float(np.clip(num / denom, 0.0, 1.0))

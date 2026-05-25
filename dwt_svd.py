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

    ll_new = ll + alpha * w_svd
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

    w_rec = (ll_stego - ll_orig) / alpha
    return np.clip(w_rec, 0, 255).astype(np.float64)


def normalized_correlation(
    watermark: np.ndarray, recovered: np.ndarray
) -> float:
    """Kurtarılan watermark ile şablon arasındaki normalleştirilmiş korelasyon (NC)."""
    w = _to_grayscale(watermark).astype(np.float64)
    r = recovered.astype(np.float64)
    r_resized = cv2.resize(r, (w.shape[1], w.shape[0]), interpolation=cv2.INTER_AREA)
    w_norm = w - w.mean()
    r_norm = r_resized - r_resized.mean()
    denom = np.linalg.norm(w_norm) * np.linalg.norm(r_norm)
    if denom < 1e-10:
        return 0.0
    return float(np.sum(w_norm * r_norm) / denom)

"""Orijinal ve DWT-SVD stego yan yana (kartal.png).

Kullanim:
  python3 demo_dwt_compare.py          # alpha=0.04 (daha gizli)
  python3 demo_dwt_compare.py 0.08     # alpha arguman
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

from video_io import VideoSource, run_preview_loop
from dwt_svd import embed, extract, normalized_correlation

WM_PATH = Path(__file__).resolve().parent / "skor.jpg"
# alpha: gomme gucu — kucuk = logo daha az belli, buyuk = daha belirgin (0.02–0.15 tipik)
DEFAULT_ALPHA = 0.004
ALPHA = float(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ALPHA
MAX_DISPLAY_WIDTH = 1280
PROCESS_MAX_WIDTH = 960  # DWT-SVD agir; canli akis icin islem cozunurlugu
_printed = 0


def _resize_frame(frame: np.ndarray, max_width: int) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame
    scale = max_width / w
    return cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def _label(frame: np.ndarray, text: str) -> np.ndarray:
    out = frame.copy()
    cv2.putText(
        out,
        text,
        (12, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    return out


def _fit_display(image: np.ndarray, max_width: int) -> np.ndarray:
    h, w = image.shape[:2]
    if w <= max_width:
        return image
    scale = max_width / w
    return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def process(frame: np.ndarray) -> np.ndarray:
    global _printed
    work = _resize_frame(frame, PROCESS_MAX_WIDTH)
    stego = embed(work, str(WM_PATH), alpha=ALPHA)

    if _printed < 3:
        recovered = extract(stego, work, alpha=ALPHA)
        nc = normalized_correlation(str(WM_PATH), recovered)
        print(f"NC (kartal): {nc:.4f}")
        _printed += 1

    combined = cv2.hconcat(
        [
            _label(work, "Orijinal"),
            _label(stego, "Watermark gomulu (DWT-SVD)"),
        ]
    )
    return _fit_display(combined, MAX_DISPLAY_WIDTH)


def main() -> None:
    if not WM_PATH.is_file():
        raise FileNotFoundError(f"Watermark bulunamadi: {WM_PATH}")
    if not 0 < ALPHA <= 1:
        raise ValueError("alpha (0, 1] araliginda olmali")

    with VideoSource(0) as src:
        print("Watermark:", WM_PATH.name)
        print("Alpha:", ALPHA)
        print("Pencere: sol orijinal, sag DWT-SVD — q ile cikis")
        run_preview_loop(
            src,
            process_fn=process,
            window_name="DWT-SVD karsilastirma (q=cikis)",
        )


if __name__ == "__main__":
    main()

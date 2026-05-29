"""LSB gizleme dogrulama — gomulen metin, extract, fark haritasi.

Kullanim:
  python3 demo_lsb_verify.py
  python3 demo_lsb_verify.py "Ozel gizli mesajim"
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

import lsb
from video_io import VideoSource

MSG = sys.argv[1] if len(sys.argv) > 1 else "Merhaba canli test"


def _diff_map(
    original: np.ndarray, stego: np.ndarray, bits_needed: int
) -> np.ndarray:
    """Gomme bolgesinde degisen pikselleri kirmizi vurgular."""
    flat_o = original.ravel()
    flat_s = stego.ravel()
    n = min(bits_needed, flat_o.size)
    tag = np.zeros(flat_o.shape, dtype=np.uint8)
    tag[:n] = (flat_o[:n] != flat_s[:n]).astype(np.uint8) * 255
    mask = tag.reshape(original.shape)
    if mask.ndim == 3:
        mask = mask.max(axis=2)
    vis = np.zeros_like(original)
    vis[:, :, 2] = mask  # kirmizi: degisen LSB bolgesi
    vis[:, :, 1] = mask // 3
    return vis


def _synthetic_frame(width: int = 640, height: int = 480) -> np.ndarray:
    x = np.linspace(0, 255, width, dtype=np.uint8)
    y = np.linspace(0, 255, height, dtype=np.uint8)
    b, g = np.meshgrid(x, y)
    frame = np.dstack([b, g, ((b.astype(np.uint16) + g) // 2).astype(np.uint8)])
    cv2.putText(
        frame,
        "Sentetik test",
        (20, height - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )
    return frame


def _capture_frame(warmup: int = 45) -> tuple[np.ndarray, str]:
    """Kamera isinsin; siyah kare gelirse sentetik kare kullan."""
    with VideoSource(0) as src:
        frame = None
        for _ in range(warmup):
            frame = src.read_frame()
        if frame is None:
            raise RuntimeError("Webcam karesi alinamadi")
        if float(frame.mean()) < 20.0:
            print(
                "Uyari: Webcam karesi cok karanlik (ilk kare?). "
                "Sentetik test goruntusu kullaniliyor."
            )
            return _synthetic_frame(), "sentetik"
        return frame, "webcam"


def _fit_panel(panel: np.ndarray, max_width: int = 1200) -> np.ndarray:
    h, w = panel.shape[:2]
    if w <= max_width:
        return np.ascontiguousarray(panel)
    scale = max_width / w
    out = cv2.resize(panel, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
    return np.ascontiguousarray(out)


def main() -> None:
    print("=== LSB ne gizliyor? ===")
    print("Tip: UTF-8 metin (payload_type=0)")
    print("Gomulen:", repr(MSG))
    print("Ham byte:", MSG.encode("utf-8"))
    print()

    frame, kaynak = _capture_frame()
    print(f"Kare kaynagi: {kaynak} (ortalama parlaklik: {frame.mean():.1f})")
    cap = lsb.calculate_capacity(frame)
    bits_needed = len(lsb.build_payload(MSG.encode("utf-8"), 0))
    print(f"Kare boyutu: {frame.shape[1]}x{frame.shape[0]}")
    print(f"Kapasite: {cap} byte | Bu mesaj: {len(MSG.encode('utf-8'))} byte | Bit: {bits_needed}")

    stego = lsb.embed(frame, MSG)
    kind, recovered = lsb.extract(stego)

    print()
    print("=== Dogrulama ===")
    print("Stego kareden cikarilan:", repr(recovered), f"({kind})")
    print("Eslesme:", recovered == MSG)

    flat_o = frame.ravel()
    flat_s = stego.ravel()
    changed = int(np.sum(flat_o[:bits_needed] != flat_s[:bits_needed]))
    outside_ok = bool(np.all(flat_o[bits_needed:] == flat_s[bits_needed:]))
    print(f"Gomme alaninda degisen deger: {changed} / {bits_needed}")
    print("Gomme disi pikseller birebir ayni:", outside_ok)

    diff = _diff_map(frame, stego, bits_needed)
    panel = _fit_panel(cv2.hconcat([frame, stego, diff]))
    h, w = panel.shape[:2]
    third = w // 3

    cv2.putText(panel, "Orijinal", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(panel, "Stego (gizli)", (third + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(
        panel,
        "LSB degisen bolge (kirmizi)",
        (2 * third + 10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
    )
    cv2.putText(
        panel,
        f"Mesaj: {MSG[:36]}",
        (10, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )

    print()
    print("Pencere: sol orijinal, orta stego, sag kirmizi=gomme bandi.")
    print("Kapatmak icin pencereye tiklayip bir tusa basin.")
    cv2.namedWindow("LSB dogrulama", cv2.WINDOW_NORMAL)
    cv2.imshow("LSB dogrulama", panel)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

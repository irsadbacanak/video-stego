"""LSB canli: orijinal | gomulu | cikarilan goruntu — python3 demo_lsb_compare.py

Metin modu: 3. panel = cikarilan metnin goruntusu.
Resim modu: python3 demo_lsb_compare.py --image kartal.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

from video_io import VideoSource, run_preview_loop
import lsb

MSG = "Merhaba canli test"
MAX_DISPLAY_WIDTH = 1400
_printed = 0

# None = metin; Path = dosya gom (ornegin kartal.png)
EMBED_IMAGE: Path | None = None
if len(sys.argv) >= 3 and sys.argv[1] == "--image":
    EMBED_IMAGE = Path(sys.argv[2]).expanduser().resolve()


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


def _wrap_text(text: str, max_chars: int = 28) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _recovered_visual(h: int, w: int, kind: str, data: str | bytes) -> np.ndarray:
    """Extract sonrasi gosterilecek goruntu: cikarilan verinin kendisi."""
    if kind == "image":
        buf = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            view = np.full((h, w, 3), 64, dtype=np.uint8)
            cv2.putText(
                view,
                "Resim decode edilemedi",
                (20, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return view
        return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)

    view = np.full((h, w, 3), 248, dtype=np.uint8)
    lines = _wrap_text(str(data), max_chars=max(12, w // 18))
    y0 = max(50, h // 2 - (len(lines) * 34) // 2)
    for i, line in enumerate(lines):
        cv2.putText(
            view,
            line,
            (24, y0 + i * 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (30, 30, 30),
            2,
            cv2.LINE_AA,
        )
    return view


def _payload_matches(kind: str, data: str | bytes) -> bool:
    if kind == "text":
        return data == MSG
    if EMBED_IMAGE is not None and EMBED_IMAGE.is_file():
        return data == EMBED_IMAGE.read_bytes()
    return kind == "image" and len(data) > 0


def _fit_display(image: np.ndarray, max_width: int) -> np.ndarray:
    h, w = image.shape[:2]
    if w <= max_width:
        return np.ascontiguousarray(image)
    scale = max_width / w
    out = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return np.ascontiguousarray(out)


def process(frame: np.ndarray) -> np.ndarray:
    global _printed
    if EMBED_IMAGE is not None:
        stego = lsb.embed_image(frame, str(EMBED_IMAGE))
    else:
        stego = lsb.embed(frame, MSG)

    kind, data = lsb.extract(stego)
    matches = _payload_matches(kind, data)
    h, w = frame.shape[:2]
    recovered_view = _recovered_visual(h, w, kind, data)

    if _printed < 3:
        if kind == "text":
            print("Cikarilan:", repr(data), f"({kind})", "| Eslesme:", matches)
        else:
            print(f"Cikarilan: image {len(data)} byte", "| Eslesme:", matches)
        _printed += 1

    status = "OK" if matches else "HATA"
    recovered_view = _label(recovered_view, f"3. Cikarilan ({status})")

    combined = cv2.hconcat(
        [
            _label(frame, "1. Orijinal"),
            _label(stego, "2. Veri gomulu (LSB)"),
            recovered_view,
        ]
    )
    return _fit_display(combined, MAX_DISPLAY_WIDTH)


def main() -> None:
    with VideoSource(0) as src:
        for _ in range(30):
            frame = src.read_frame()
        cap = lsb.calculate_capacity(frame) if frame is not None else 0
        print("Kapasite (byte):", cap)
        if EMBED_IMAGE:
            print("Gomulu dosya:", EMBED_IMAGE)
        else:
            print("Gomulu mesaj:", MSG)
        print("Pencere: orijinal | gomulu | cikarilan goruntu — q ile cikis")
        run_preview_loop(
            src,
            process_fn=process,
            window_name="LSB karsilastirma (q=cikis)",
        )


if __name__ == "__main__":
    main()

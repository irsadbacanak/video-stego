"""Video I/O altyapısı — Kişi 1"""

from __future__ import annotations

import cv2
import numpy as np


class VideoSource:
    """Webcam veya video dosyasından kare okuma."""

    def __init__(self, source: int | str = 0) -> None:
        self._source = source
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self._source)
        return self._cap.isOpened()

    def read_frame(self) -> np.ndarray | None:
        if self._cap is None or not self._cap.isOpened():
            return None
        ret, frame = self._cap.read()
        return frame if ret else None

    def get_fps(self) -> float:
        if self._cap is None:
            return 0.0
        return self._cap.get(cv2.CAP_PROP_FPS)

    def get_resolution(self) -> tuple[int, int]:
        if self._cap is None:
            return (0, 0)
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (w, h)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "VideoSource":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.release()


class VideoWriter:
    """BGR kareleri video dosyasına yazar."""

    def __init__(
        self,
        path: str,
        fps: float,
        resolution: tuple[int, int],
        codec: str = "mp4v",
    ) -> None:
        self._path = path
        self._fps = fps
        self._resolution = resolution
        self._fourcc = cv2.VideoWriter_fourcc(*codec)
        self._writer: cv2.VideoWriter | None = None

    def _ensure_open(self) -> None:
        if self._writer is None:
            self._writer = cv2.VideoWriter(
                self._path, self._fourcc, self._fps, self._resolution
            )

    def write_frame(self, frame: np.ndarray) -> None:
        self._ensure_open()
        self._writer.write(frame)  # type: ignore[union-attr]

    def release(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def __enter__(self) -> "VideoWriter":
        return self

    def __exit__(self, *_) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Renk kanalı dönüşümleri
# ---------------------------------------------------------------------------

def bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def split_rgb(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """BGR girişten R, G, B kanallarını döndürür."""
    rgb = bgr_to_rgb(frame)
    r, g, b = cv2.split(rgb)
    return r, g, b


def split_ycbcr(
    frame: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """BGR girişten Y, Cb, Cr kanallarını döndürür."""
    ycbcr = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    # OpenCV sırası: Y, Cr, Cb — biz Y, Cb, Cr olarak döndürüyoruz
    y, cr, cb = cv2.split(ycbcr)
    return y, cb, cr


def merge_ycbcr(
    Y: np.ndarray, Cb: np.ndarray, Cr: np.ndarray
) -> np.ndarray:
    """Y, Cb, Cr kanallarını birleştirip BGR kare döndürür."""
    ycbcr = cv2.merge([Y, Cr, Cb])  # OpenCV sırası Y, Cr, Cb
    return cv2.cvtColor(ycbcr, cv2.COLOR_YCrCb2BGR)


# ---------------------------------------------------------------------------
# Önizleme
# ---------------------------------------------------------------------------

def preview_frame(
    frame: np.ndarray,
    window_name: str = "Preview",
    wait_ms: int = 1,
) -> bool:
    """Kareyi gösterir; 'q' tuşuna basılırsa True döner (çıkış sinyali)."""
    cv2.imshow(window_name, frame)
    return cv2.waitKey(wait_ms) & 0xFF == ord("q")


def run_preview_loop(
    source: VideoSource,
    process_fn=None,
    window_name: str = "Preview",
) -> None:
    """
    VideoSource'dan sürekli kare okuyarak önizleme döngüsü çalıştırır.

    process_fn: frame -> frame  dönüşüm fonksiyonu (isteğe bağlı)
    'q' tuşu veya kaynak bitmesiyle döngü durur.
    """
    try:
        while True:
            frame = source.read_frame()
            if frame is None:
                break
            if process_fn is not None:
                frame = process_fn(frame)
            if preview_frame(frame, window_name=window_name):
                break
    finally:
        cv2.destroyWindow(window_name)

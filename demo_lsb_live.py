"""Canlı webcam LSB demo — python3 demo_lsb_live.py (q ile çıkış)."""

from video_io import VideoSource, run_preview_loop
import lsb

MSG = "Merhaba canli test"
_printed = 0


def process(frame):
    global _printed
    stego = lsb.embed(frame, MSG)
    if _printed < 5:
        kind, data = lsb.extract(stego)
        print("Cikarilan:", repr(data), f"({kind})")
        _printed += 1
    return stego


def main():
    with VideoSource(0) as src:
        frame = src.read_frame()
        cap = lsb.calculate_capacity(frame) if frame is not None else 0
        print("Kapasite (byte):", cap)
        print("Gomulu mesaj:", MSG)
        run_preview_loop(src, process_fn=process, window_name="LSB stego (q=cikis)")


if __name__ == "__main__":
    main()

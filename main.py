"""Entegrasyon iskeleti — tüm modülleri bir araya getirir."""

import sys

from video_io import VideoSource, VideoWriter, split_ycbcr, merge_ycbcr, run_preview_loop
import lsb       # Kişi 2
import dwt_svd   # Kişi 3
import metrics   # Kişi 4
import ui        # Kişi 4


def demo_passthrough(input_path: str, output_path: str) -> None:
    """Videoyu olduğu gibi okuyup yeni dosyaya yazar (pipeline testi)."""
    with VideoSource(input_path) as src, \
         VideoWriter(output_path, src.get_fps(), src.get_resolution()) as writer:
        frame_count = 0
        while True:
            frame = src.read_frame()
            if frame is None:
                break
            writer.write_frame(frame)
            frame_count += 1
        print(f"Passthrough tamamlandı: {frame_count} kare → {output_path}")


def demo_webcam_preview() -> None:
    """Webcam'i açıp canlı önizleme gösterir ('q' ile çıkış)."""
    with VideoSource(0) as src:
        print(f"Webcam açıldı — {src.get_resolution()} @ {src.get_fps():.1f} fps")
        run_preview_loop(src)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        demo_passthrough(sys.argv[1], sys.argv[2])
    else:
        demo_webcam_preview()

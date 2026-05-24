# Video Steganografi Projesi

4 kişilik ekip projesi. Her modül ayrı bir kişi tarafından geliştirilmektedir.

## Proje Yapısı

```
veri-gizleme/
├── video_io.py    — Video altyapısı (Kişi 1) ✅
├── lsb.py         — LSB steganografi (Kişi 2) ✅
├── dwt_svd.py     — DWT-SVD watermarking (Kişi 3) 🔲
├── metrics.py     — Kalite metrikleri (Kişi 4) 🔲
├── ui.py          — Arayüz (Kişi 4) 🔲
├── main.py        — Entegrasyon iskeleti
└── requirements.txt
```

## Kurulum

```bash
pip install -r requirements.txt
```

## Kullanım

```bash
python3 main.py                        # webcam önizleme
python3 main.py input.mp4 output.mp4   # video passthrough
```

---

## Modül Durumları

### ✅ video_io.py — Kişi 1 (Tamamlandı)

**Neler yapıldı:**
- `VideoSource` — webcam ve video dosyasından kare okuma, fps/çözünürlük sorgulama
- `VideoWriter` — BGR kare yazma, MP4 çıktı
- `split_ycbcr` / `merge_ycbcr` — YCbCr kanal ayrıştırma ve birleştirme
- `split_rgb` — RGB kanal ayrıştırma
- `bgr_to_rgb` / `rgb_to_bgr` — renk uzayı dönüşümleri
- `preview_frame` / `run_preview_loop` — gerçek zamanlı webcam önizleme, işleme callback desteği

**Testler:**

```bash
# 1. Import ve sözdizimi kontrolü
python3 -c "from video_io import VideoSource, VideoWriter, split_ycbcr, merge_ycbcr, split_rgb; print('OK')"

# 2. YCbCr round-trip (max 1 piksel yuvarlama hatası beklenir)
python3 -c "
import numpy as np
from video_io import split_ycbcr, merge_ycbcr
frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
Y, Cb, Cr = split_ycbcr(frame)
back = merge_ycbcr(Y, Cb, Cr)
print('Max fark:', np.abs(frame.astype(int) - back.astype(int)).max())
"

# 3. Video passthrough (sentetik video oluşturup yazar, okur)
python3 -c "
import numpy as np, cv2
out = cv2.VideoWriter('/tmp/test_in.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (640,480))
[out.write(np.full((480,640,3), i*8%256, dtype=np.uint8)) for i in range(30)]
out.release()
"
python3 main.py /tmp/test_in.mp4 /tmp/test_out.mp4

# 4. Webcam bağlantı testi
python3 -c "
from video_io import VideoSource
with VideoSource(0) as s:
    print('Çözünürlük:', s.get_resolution(), '@ FPS:', s.get_fps())
"

# 5. Grayscale callback ile webcam önizleme (q ile kapat)
python3 -c "
import cv2
from video_io import VideoSource, run_preview_loop
with VideoSource(0) as src:
    run_preview_loop(src, process_fn=lambda f: cv2.cvtColor(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR))
"
```

---

### ✅ lsb.py — Kişi 2 (Tamamlandı)

- `embed(frame, message)` — mesajı kareye göm
- `extract(frame)` — kareden mesajı çıkar

**Neler yapıldı:**

- `embed` — Metni video karesine LSB yöntemiyle gömer
- `embed_image` — Resim dosyasını video karesine gömer
- `extract` — Stego kareden metin veya resmi geri çıkarır
- `calculate_capacity` — Bir kareye kaç byte sığacağını hesaplar
- `build_payload` / `parse_payload` — Header sistemi (tip + boyut bilgisi)
- `bytes_to_bits` / `bits_to_bytes` — Bit dönüşüm yardımcıları
- `calculate_psnr` / `calculate_ssim` / `calculate_ber` — Kalite metrikleri
- `evaluate` — Tek fonksiyonla tüm metrikleri hesaplar ve raporlar

**Özellikler:**

- Metin ve resim gömme desteği
- Header sistemi sayesinde payload tipi ve boyutu otomatik algılanır
- Kişi 1'in `VideoSource` / `VideoWriter` sınıflarıyla tam uyumlu
- Her kareye bağımsız gömme/çıkarma yapılabilir

**Test Sonuçları:**

Kısa metin (31 byte):
- PSNR: 88.85 dB ✅ (40 dB üzeri gözle fark edilmez)
- SSIM: 1.0000 ✅ (birebir görsel kalite)
- BER:  0.0000 ✅ (sıfır bit hatası)
- Doluluk: %0.014

Uzun metin (10.000 karakter):
- PSNR: 64.30 dB ✅
- SSIM: 0.9998 ✅
- BER:  0.0000 ✅
- Doluluk: %4.52

Resim gömme (13.448 byte):
- PSNR: 63.29 dB ✅
- SSIM: 0.9997 ✅
- BER:  0.0000 ✅ (resim birebir çıkarıldı)
- Doluluk: %6.08

- 
- > Doluluk arttıkça PSNR düşmektedir, bu LSB yönteminin beklenen davranışıdır.
> Tüm testlerde BER = 0.0000, veri kayıpsız iletim sağlanmıştır.

### 🔲 dwt_svd.py — Kişi 3 (Yapılacak)

- `embed(frame, watermark, alpha=0.1)` — frekans alanında watermark göm
- `extract(frame, original)` — watermark çıkar

---

### 🔲 metrics.py — Kişi 4 (Yapılacak)

- `psnr(original, stego)` — Peak Signal-to-Noise Ratio
- `ssim(original, stego)` — Structural Similarity Index
- `ber(original_msg, extracted_msg)` — Bit Error Rate

### 🔲 ui.py — Kişi 4 (Yapılacak)

- `launch()` — grafik arayüz

---

## Bağımlılıklar

| Paket | Versiyon |
|---|---|
| opencv-python | ≥ 4.8 |
| numpy | ≥ 1.24 |

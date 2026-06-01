"""Streamlit arayuzu — streamlit run ui.py"""

from __future__ import annotations

import cv2
import numpy as np
import pandas as pd
import streamlit as st

import dwt_svd
import lsb
import metrics
from video_io import VideoSource

DEFAULT_MSG = "Gizli Bilgi"
_DISPLAY_MAX_W = 640
_COMPARE_MAX_W = 480  # 3 panel yan yana için daha dar


def create_text_watermark(text: str) -> np.ndarray:
    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.putText(img, text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
    return img


def _decode_upload(upload) -> np.ndarray | None:
    if upload is None:
        return None
    file_bytes = np.asarray(bytearray(upload.getvalue()), dtype=np.uint8)
    return cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)


def _resize(frame: np.ndarray, max_w: int) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= max_w:
        return frame
    scale = max_w / w
    return cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def _embed_frame(frame: np.ndarray, payload, ptype: str, alpha: float = 0.08) -> np.ndarray:
    if ptype == "Metin":
        return lsb.embed(frame.copy(), str(payload))
    return dwt_svd.embed(frame.copy(), payload, alpha=alpha)


def _label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.putText(out, text, (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
    return out


def _open_cap(key: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(0)
    for _ in range(15):
        cap.read()
    st.session_state[key] = cap
    return cap


def _release_cap(key: str) -> None:
    cap = st.session_state.get(key)
    if cap is not None:
        cap.release()
        st.session_state[key] = None


# ─────────────────────────────────────────────
# Fragment 1: Canlı Yayın
# ─────────────────────────────────────────────
@st.fragment(run_every=0.1)
def _live_stream() -> None:
    if not st.session_state.get("live_running"):
        return

    cap = st.session_state["cap"] or _open_cap("cap")

    ret, frame = cap.read()
    if not ret or frame is None:
        st.error("Kamera karesi alinamadi.")
        st.session_state["live_running"] = False
        _release_cap("cap")
        return

    frame = _resize(frame, _DISPLAY_MAX_W)
    payload = st.session_state.get("payload_data")
    ptype   = st.session_state.get("payload_type", "Metin")
    alpha   = st.session_state.get("wm_alpha", 0.08)

    try:
        stego = _embed_frame(frame, payload, ptype, alpha)
        st.session_state["last_original"] = frame.copy()
        st.session_state["last_stego"]    = stego.copy()

        if ptype == "Resim/Logo" and payload is not None:
            wm_bgr = cv2.cvtColor(
                cv2.resize(payload, (frame.shape[1] // 2, frame.shape[0]),
                           interpolation=cv2.INTER_AREA),
                cv2.COLOR_GRAY2BGR,
            )
            panel = np.hstack([
                _label(frame,  "Orijinal"),
                _label(stego,  f"DWT-SVD (a={alpha:.2f})"),
                _label(wm_bgr, "Gomulu logo"),
            ])
            caption = f"Alpha: {alpha:.2f} — Logo DWT-SVD ile gomuldu"
        else:
            panel = np.hstack([
                _label(frame,  "Orijinal"),
                _label(stego,  "LSB gomulu"),
            ])
            caption = f"Gomulu mesaj: {payload!r}"

        _, buf = cv2.imencode(".jpg", panel, [cv2.IMWRITE_JPEG_QUALITY, 80])
        st.image(buf.tobytes(), width="stretch")
        st.caption(caption)

    except Exception as e:
        st.error(f"Gomme hatasi: {e}")
        st.session_state["live_running"] = False


# ─────────────────────────────────────────────
# Fragment 2: Canlı Karşılaştırmalı Analiz
# ─────────────────────────────────────────────
@st.fragment(run_every=0.1)
def _compare_stream() -> None:
    if not st.session_state.get("compare_running"):
        return

    cap = st.session_state["compare_cap"] or _open_cap("compare_cap")

    ret, frame = cap.read()
    if not ret or frame is None:
        st.error("Kamera karesi alinamadi.")
        st.session_state["compare_running"] = False
        _release_cap("compare_cap")
        return

    frame = _resize(frame, _COMPARE_MAX_W)
    msg   = st.session_state.get("cmp_msg", DEFAULT_MSG)
    wm    = st.session_state.get("cmp_wm")
    alpha = st.session_state.get("cmp_alpha", 0.08)

    if wm is None:
        wm = create_text_watermark(msg)

    try:
        s_lsb = lsb.embed(frame.copy(), msg)
        s_dwt = dwt_svd.embed(frame.copy(), wm, alpha=alpha)

        # LSB metrikleri
        psnr_lsb = metrics.psnr(frame, s_lsb)
        rs_lsb   = metrics.rs_analysis(s_lsb)
        ssim_lsb = metrics.ssim(frame, s_lsb)

        # DWT-SVD metrikleri
        psnr_dwt = metrics.psnr(frame, s_dwt)
        ssim_dwt = metrics.ssim(frame, s_dwt)
        recovered = dwt_svd.extract(s_dwt, frame, alpha=alpha)
        nc_dwt   = dwt_svd.normalized_correlation(wm, recovered)

        # 3 panel: Orijinal | LSB | DWT-SVD
        panel = np.hstack([
            _label(frame,  "Orijinal"),
            _label(s_lsb,  f"LSB  PSNR:{psnr_lsb:.1f}dB"),
            _label(s_dwt,  f"DWT-SVD  PSNR:{psnr_dwt:.1f}dB"),
        ])
        _, buf = cv2.imencode(".jpg", panel, [cv2.IMWRITE_JPEG_QUALITY, 80])
        st.image(buf.tobytes(), width="stretch")

        # LSB metrikleri
        st.markdown("**LSB**")
        m1, m2, m3 = st.columns(3)
        m1.metric("PSNR", f"{psnr_lsb:.2f} dB")
        m2.metric("RS",   f"{rs_lsb:.3f}",
                  delta="Riskli" if rs_lsb > 0.3 else "Guvenli",
                  delta_color="inverse")
        m3.metric("SSIM", f"{ssim_lsb:.4f}")

        # DWT-SVD metrikleri
        st.markdown("**DWT-SVD**")
        m4, m5, m6 = st.columns(3)
        m4.metric("PSNR", f"{psnr_dwt:.2f} dB")
        m5.metric("SSIM", f"{ssim_dwt:.4f}")
        m6.metric("NC",   f"{nc_dwt:.4f}",
                  delta="Iyi" if nc_dwt > 0.7 else "Zayif",
                  delta_color="normal" if nc_dwt > 0.7 else "inverse")

        # LSB'den çıkarılan veri
        st.markdown("**LSB — Cikartilan Veri**")
        try:
            kind, extracted_text = lsb.extract(s_lsb)
            if kind == "text":
                st.success(f"📝 {extracted_text}")
            else:
                st.info("Gizlenen veri metin degil (resim/binary).")
        except Exception as ex:
            st.warning(f"Veri cikarilamadi: {ex}")

    except Exception as e:
        st.error(f"Karsilastirma hatasi: {e}")
        st.session_state["compare_running"] = False


# ─────────────────────────────────────────────
# Ana uygulama
# ─────────────────────────────────────────────
def launch() -> None:
    st.set_page_config(page_title="Steganografi Analiz Paneli", layout="wide")

    for key, default in [
        ("last_original", None),
        ("last_stego", None),
        ("payload_data", DEFAULT_MSG),
        ("payload_type", "Metin"),
        ("wm_alpha", 0.08),
        ("live_running", False),
        ("cap", None),
        ("compare_running", False),
        ("compare_cap", None),
        ("cmp_msg", DEFAULT_MSG),
        ("cmp_wm", None),
        ("cmp_alpha", 0.08),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    mode = st.sidebar.radio(
        "Islem seciniz:",
        ["Canli Yayin (Webcam)", "Karsilastirmali Analiz"],
    )

    # Mod değişince diğer akışı kapat
    if mode == "Canli Yayin (Webcam)" and st.session_state["compare_running"]:
        st.session_state["compare_running"] = False
        _release_cap("compare_cap")
    if mode == "Karsilastirmali Analiz" and st.session_state["live_running"]:
        st.session_state["live_running"] = False
        _release_cap("cap")

    st.title("Canli Video Steganografi Projesi")
    st.caption("LSB (metin) ve DWT-SVD (logo) — tarayicida onizleme")

    # ── MOD 1: Canlı Yayın ──────────────────────────────────────────
    if mode == "Canli Yayin (Webcam)":
        st.header("1. Veri hazirlama")
        ptype = st.radio(
            "Gizlenecek veri turu:",
            ["Metin", "Resim/Logo (DWT-SVD)"],
            horizontal=True,
        )
        ptype_key = "Metin" if ptype == "Metin" else "Resim/Logo"

        payload = None
        if ptype_key == "Metin":
            payload = st.text_input("Mesaj:", DEFAULT_MSG)
        else:
            up = st.file_uploader(
                "Gomulecek logo / resim yukle (PNG, JPG)",
                type=["png", "jpg", "jpeg"],
            )
            payload = _decode_upload(up)
            if up is not None and payload is None:
                st.error("Dosya okunamadi.")
            elif payload is not None:
                col_prev, col_info = st.columns([1, 2])
                with col_prev:
                    st.image(payload, caption="Yuklenecek logo", width=160)
                with col_info:
                    st.info(
                        f"Boyut: {payload.shape[1]}×{payload.shape[0]} px\n\n"
                        "Logo DWT-SVD ile video karelerine gomulecek."
                    )
                col_sl, col_num = st.columns([3, 1])
                with col_sl:
                    alpha_val = st.slider(
                        "Gomme gucu (alpha)",
                        min_value=0.02, max_value=0.20,
                        value=float(st.session_state["wm_alpha"]),
                        step=0.01,
                    )
                with col_num:
                    alpha_val = st.number_input(
                        "Elle gir", min_value=0.01, max_value=1.0,
                        value=alpha_val, step=0.01, format="%.2f",
                    )
                st.session_state["wm_alpha"] = alpha_val

        st.header("2. Canli Akim")
        col_start, col_stop = st.columns(2)
        with col_start:
            start_clicked = st.button("Akisi baslat", type="primary",
                                      disabled=st.session_state["live_running"])
        with col_stop:
            stop_clicked = st.button("Durdur",
                                     disabled=not st.session_state["live_running"])

        if start_clicked:
            if ptype_key == "Resim/Logo" and payload is None:
                st.warning("Once logo/resim yukleyin.")
            elif ptype_key == "Metin" and not str(payload).strip():
                st.warning("Mesaj bos olamaz.")
            else:
                st.session_state.update(
                    payload_data=payload, payload_type=ptype_key, live_running=True
                )
                st.rerun()

        if stop_clicked:
            st.session_state["live_running"] = False
            _release_cap("cap")
            st.rerun()

        if st.session_state["live_running"]:
            st.subheader("3. Canli Onizleme")
            _live_stream()
        elif st.session_state["last_original"] is not None:
            st.info("Akim durduruldu. Son islenen kare asagida.")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Son orijinal kare")
                st.image(st.session_state["last_original"], channels="BGR", width="stretch")
            with c2:
                st.caption("Son veri gomulu kare")
                st.image(st.session_state["last_stego"], channels="BGR", width="stretch")

    # ── MOD 2: Karşılaştırmalı Analiz ───────────────────────────────
    else:
        st.header("Canli Karsilastirmali Analiz")
        st.caption("Her kare icin LSB ve DWT-SVD ayni anda uygulanir; metrikler anlik guncellenir.")

        st.subheader("1. Parametreler")
        cmp_msg = st.text_input("LSB mesaji:", st.session_state["cmp_msg"])
        st.session_state["cmp_msg"] = cmp_msg

        up_cmp = st.file_uploader(
            "DWT-SVD logosu (yuklemezsen metin watermark kullanilir)",
            type=["png", "jpg", "jpeg"],
            key="cmp_upload",
        )
        if up_cmp is not None:
            wm = _decode_upload(up_cmp)
            if wm is not None:
                st.session_state["cmp_wm"] = wm
                col_p, col_i = st.columns([1, 3])
                with col_p:
                    st.image(wm, caption="DWT-SVD logosu", width=120)
                with col_i:
                    st.info(f"Boyut: {wm.shape[1]}×{wm.shape[0]} px")

        col_sl, col_num = st.columns([3, 1])
        with col_sl:
            cmp_alpha = st.slider(
                "DWT-SVD alpha",
                min_value=0.02, max_value=0.20,
                value=float(st.session_state["cmp_alpha"]),
                step=0.01,
            )
        with col_num:
            cmp_alpha = st.number_input(
                "Elle gir", min_value=0.01, max_value=1.0,
                value=cmp_alpha, step=0.01, format="%.2f",
                key="cmp_alpha_input",
            )
        st.session_state["cmp_alpha"] = cmp_alpha

        st.subheader("2. Canli Akim")
        col_start, col_stop = st.columns(2)
        with col_start:
            cmp_start = st.button("Karsilastirmayi baslat", type="primary",
                                  disabled=st.session_state["compare_running"])
        with col_stop:
            cmp_stop = st.button("Durdur ",
                                 disabled=not st.session_state["compare_running"])

        if cmp_start:
            if not str(cmp_msg).strip():
                st.warning("LSB mesaji bos olamaz.")
            else:
                st.session_state["compare_running"] = True
                st.rerun()

        if cmp_stop:
            st.session_state["compare_running"] = False
            _release_cap("compare_cap")
            st.rerun()

        if st.session_state["compare_running"]:
            st.subheader("3. Canli Sonuclar — Orijinal | LSB | DWT-SVD")
            _compare_stream()
        else:
            st.info("Parametreleri ayarlayip 'Karsilastirmayi baslat' butonuna basin.")


if __name__ == "__main__":
    launch()

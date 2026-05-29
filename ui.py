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


def create_text_watermark(text: str) -> np.ndarray:
    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.putText(img, text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
    return img


def _decode_upload(upload) -> np.ndarray | None:
    if upload is None:
        return None
    file_bytes = np.asarray(bytearray(upload.getvalue()), dtype=np.uint8)
    return cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)


def _embed_frame(frame: np.ndarray, payload, ptype: str) -> np.ndarray:
    if ptype == "Metin":
        return lsb.embed(frame.copy(), str(payload))
    return dwt_svd.embed(frame.copy(), payload, alpha=0.04)


def _payload_for_compare(data, ptype: str):
    if ptype == "Metin":
        return str(data), create_text_watermark(str(data))
    return data, data


def _capture_webcam_frame(warmup: int = 30) -> np.ndarray | None:
    with VideoSource(0) as src:
        frame = None
        for _ in range(warmup):
            frame = src.read_frame()
        return frame


def launch() -> None:
    st.set_page_config(page_title="Steganografi Analiz Paneli", layout="wide")

    if "last_original" not in st.session_state:
        st.session_state["last_original"] = None
    if "last_stego" not in st.session_state:
        st.session_state["last_stego"] = None
    if "payload_data" not in st.session_state:
        st.session_state["payload_data"] = DEFAULT_MSG
    if "payload_type" not in st.session_state:
        st.session_state["payload_type"] = "Metin"

    mode = st.sidebar.radio(
        "Islem seciniz:",
        ["Canli Yayin (Webcam)", "Karsilastirmali Analiz"],
    )

    st.title("Canli Video Steganografi Projesi")
    st.caption("LSB (metin) ve DWT-SVD (logo) — tarayicida onizleme")

    if mode == "Canli Yayin (Webcam)":
        st.header("1. Veri hazirlama")
        ptype = st.radio(
            "Gizlenecek veri turu:",
            ["Metin", "Resim/Logo"],
            horizontal=True,
        )

        payload = None
        if ptype == "Metin":
            payload = st.text_input("Mesaj:", DEFAULT_MSG)
        else:
            up = st.file_uploader("Logo/resim yukle", type=["png", "jpg", "jpeg"])
            payload = _decode_upload(up)
            if up and payload is None:
                st.error("Dosya okunamadi.")

        st.header("2. Kare al ve gom")
        st.info(
            "Asagidaki buton webcam'den **tek kare** alir; sonuc **bu sayfada** "
            "orijinal ve gomulu olarak gosterilir. (Ayri OpenCV penceresi acilmaz.)"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            use_camera_widget = st.checkbox("Tarayici kamerasi kullan (izin ver)", value=False)
        with col_b:
            grab = st.button("Webcam'den kare al ve gom", type="primary")

        frame = None
        if use_camera_widget:
            shot = st.camera_input("Kameradan cek")
            if shot is not None:
                file_bytes = np.asarray(bytearray(shot.getvalue()), dtype=np.uint8)
                frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if grab:
            if ptype == "Resim/Logo" and payload is None:
                st.warning("Once logo/resim yukleyin.")
            else:
                with st.spinner("Kamera aciliyor..."):
                    frame = _capture_webcam_frame()
                if frame is None:
                    st.error("Webcam karesi alinamadi. Kamera iznini kontrol edin.")
                else:
                    st.success(f"Kare alindi: {frame.shape[1]}x{frame.shape[0]}")

        if frame is not None:
            if ptype == "Metin" and not str(payload).strip():
                st.warning("Mesaj bos olamaz.")
            elif ptype == "Resim/Logo" and payload is None:
                st.warning("Logo yukleyin.")
            else:
                try:
                    stego = _embed_frame(frame, payload, ptype)
                    st.session_state["last_original"] = frame.copy()
                    st.session_state["last_stego"] = stego.copy()
                    st.session_state["payload_data"] = payload
                    st.session_state["payload_type"] = ptype
                except Exception as e:
                    st.error(f"Gomme hatasi: {e}")

        if st.session_state["last_original"] is not None:
            st.header("3. Onizleme")
            o = st.session_state["last_original"]
            s = st.session_state["last_stego"]
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Orijinal")
                st.image(o, channels="BGR", use_container_width=True)
            with c2:
                st.subheader("Veri gomulu")
                st.image(s, channels="BGR", use_container_width=True)

            if st.session_state["payload_type"] == "Metin":
                try:
                    kind, text = lsb.extract(s)
                    st.success(f"Cikarilan metin ({kind}): {text!r}")
                except Exception as e:
                    st.warning(f"Extract: {e}")
            else:
                st.caption("DWT-SVD: logo frekans alaninda gomuldu; karsilastirma modunda metrikleri gorebilirsiniz.")

    else:
        st.header("Algoritma kiyaslama")
        if st.session_state["last_original"] is None:
            st.warning(
                "Henuz kare yok. Once **Canli Yayin** modunda "
                "'Webcam'den kare al ve gom' ile bir kare isleyin."
            )
        else:
            st.success("Son islenen kare hazir. Asagidan analizi baslatin.")

        if st.button("Her iki algoritmayi test et", type="primary"):
            orig = st.session_state.get("last_original")
            data = st.session_state.get("payload_data")
            ptype = st.session_state.get("payload_type")

            if orig is None or data is None:
                st.error("Once canli modda kare alin.")
            else:
                lsb_payload, dwt_payload = _payload_for_compare(data, ptype)
                try:
                    if ptype == "Metin":
                        s_lsb = lsb.embed(orig.copy(), lsb_payload)
                    else:
                        s_lsb = lsb.embed(orig.copy(), data)

                    s_dwt = dwt_svd.embed(orig.copy(), dwt_payload, alpha=0.04)

                    psnr_lsb = metrics.psnr(orig, s_lsb)
                    psnr_dwt = metrics.psnr(orig, s_dwt)
                    rs_lsb = metrics.rs_analysis(s_lsb)
                    rs_dwt = metrics.rs_analysis(s_dwt)

                    c1, c2 = st.columns(2)
                    for col, name, res, p, r in [
                        (c1, "LSB", s_lsb, psnr_lsb, rs_lsb),
                        (c2, "DWT-SVD", s_dwt, psnr_dwt, rs_dwt),
                    ]:
                        with col:
                            st.subheader(name)
                            st.image(res, channels="BGR", use_container_width=True)
                            st.metric("PSNR (dB)", f"{p:.2f}")
                            st.markdown(
                                f"RS analizi: {'Riskli' if r > 0.3 else 'Guvenli'} ({r:.3f})"
                            )

                    st.divider()
                    st.subheader("Performans grafikleri")
                    chart_data = pd.DataFrame(
                        {
                            "Algoritma": ["LSB", "DWT-SVD"],
                            "PSNR (dB)": [psnr_lsb, psnr_dwt],
                            "Risk Skoru": [rs_lsb, rs_dwt],
                        }
                    ).set_index("Algoritma")

                    g1, g2 = st.columns(2)
                    with g1:
                        st.bar_chart(chart_data["PSNR (dB)"])
                    with g2:
                        st.bar_chart(chart_data["Risk Skoru"])

                except Exception as e:
                    st.error(f"Algoritma hatasi: {e}")


if __name__ == "__main__":
    launch()

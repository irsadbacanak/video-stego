import streamlit as st
import cv2
import numpy as np
import pandas as pd # Grafik için gerekli

from video_io import VideoSource, run_preview_loop
import lsb
import dwt_svd
import metrics

def create_text_watermark(text: str) -> np.ndarray:
    img = np.zeros((300, 300), dtype=np.uint8) 
    cv2.putText(img, text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
    return img

def launch():
    st.set_page_config(page_title="Steganografi Analiz Paneli", layout="wide")
    if 'last_original' not in st.session_state: st.session_state['last_original'] = None

    mode = st.sidebar.radio("İşlem Seçiniz:", ["Canlı Yayın (Webcam)", "Karşılaştırmalı Analiz"])
    st.title("🎥 Canlı Video Steganografi Projesi")

    # --- CANLI YAYIN ---
    if mode == "Canlı Yayın (Webcam)":
        st.header("Veri Hazırlama")
        ptype = st.radio("Gizlenecek Veri Türü:", ["Metin", "Resim/Logo"], horizontal=True)
        
        data = None
        if ptype == "Metin":
            data = st.text_input("Mesaj:", "Gizli Bilgi")
        else:
            up = st.file_uploader("Logo/Resim Yükle", type=["png", "jpg"])
            if up:
                file_bytes = np.asarray(bytearray(up.read()), dtype=np.uint8)
                data = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
        
        if st.button("Kamerayı Başlat"):
            if data is not None:
                st.session_state['payload_data'], st.session_state['payload_type'] = data, ptype
                st.info("Kamera başlatılıyor...")
                
                def process_frame(frame):
                    st.session_state['last_original'] = frame.copy()
                    try:
                        return lsb.embed(frame.copy(), data) if ptype == "Metin" else dwt_svd.embed(frame.copy(), data)
                    except: return frame
                
                with VideoSource(0) as src: run_preview_loop(src, process_fn=process_frame, window_name="Live Preview")
                st.success("Analiz için hazır.")
            else: st.warning("Lütfen veri girin.")

    # --- KARŞILAŞTIRMALI ANALİZ ---
    elif mode == "Karşılaştırmalı Analiz":
        st.header("Algoritma Kıyaslama Paneli")
        if st.button("🚀 Her İki Algoritmayı Test Et"):
            orig, data, ptype = st.session_state.get('last_original'), st.session_state.get('payload_data'), st.session_state.get('payload_type')
            
            if orig is not None and data is not None:
                d_lsb = cv2.resize(data, (64, 64)) if isinstance(data, np.ndarray) else data
                d_dwt = create_text_watermark(data) if ptype == "Metin" else data
                
                try:
                    s_lsb = lsb.embed(orig.copy(), d_lsb)
                    s_dwt = dwt_svd.embed(orig.copy(), d_dwt)
                    
                    # Metrik hesaplamaları
                    psnr_lsb, psnr_dwt = metrics.psnr(orig, s_lsb), metrics.psnr(orig, s_dwt)
                    rs_lsb, rs_dwt = metrics.rs_analysis(s_lsb), metrics.rs_analysis(s_dwt)
                    
                    # Yan yana sütunlar
                    c1, c2 = st.columns(2)
                    for i, (name, res, p, r) in enumerate([("LSB", s_lsb, psnr_lsb, rs_lsb), ("DWT-SVD", s_dwt, psnr_dwt, rs_dwt)]):
                        with [c1, c2][i]:
                            st.subheader(name)
                            st.image(res, channels="BGR", use_container_width=True)
                            st.metric("PSNR (dB)", f"{p:.2f}")
                            st.markdown(f"RS Analizi: {'🚨 Riskli' if r > 0.3 else '✅ Güvenli'}")
                    
                    # --- GRAFİKLER ---
                    st.divider()
                    st.subheader("📊 Performans Grafikleri")
                    chart_data = pd.DataFrame({
                        "Algoritma": ["LSB", "DWT-SVD"],
                        "PSNR (dB)": [psnr_lsb, psnr_dwt],
                        "Risk Skoru": [rs_lsb, rs_dwt]
                    }).set_index("Algoritma")
                    
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.write("PSNR Kıyaslaması (Yüksek daha iyi)")
                        st.bar_chart(chart_data["PSNR (dB)"])
                    with col_g2:
                        st.write("RS Analizi Risk Skoru (Düşük daha iyi)")
                        st.bar_chart(chart_data["Risk Skoru"])
                        
                except Exception as e: st.error(f"Algoritma Hatası: {e}")
            else: st.error("Önce canlı yayını başlatmalısın.")

if __name__ == "__main__":
    launch()
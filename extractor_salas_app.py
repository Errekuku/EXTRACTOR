import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import pytesseract
import cv2
import numpy as np
from fpdf import FPDF
import tempfile
import os

st.title("Extractor de Salas desde Plano PDF")

uploaded_file = st.file_uploader("Sube el plano en PDF", type=["pdf"])

if uploaded_file:
    st.success("PDF cargado correctamente. Procesando...")

    # Guardar PDF temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(uploaded_file.read())
        tmp_pdf_path = tmp_pdf.name

    # Leer PDF
    doc = fitz.open(tmp_pdf_path)
    page = doc.load_page(0)
    zoom = 6
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")

    # Mostrar imagen renderizada
    st.image(img_bytes, caption="Plano renderizado", use_column_width=True)

    # OCR
    image = Image.open(io.BytesIO(img_bytes))
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, config='--oem 3 --psm 6', output_type=pytesseract.Output.DICT)

    rooms = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if "SALA" in text.upper() or ("SUP" in text.upper() and "M2" in text.upper()):
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            rooms.append({"text": text, "bbox": (x, y, w, h)})

    if not rooms:
        st.warning("No se detectaron salas. Asegúrate de que el plano contenga nombres visibles.")
    else:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        scale_factor = 0.15  # Escalado para que quepan bien en A4

        for room in rooms:
            x, y, w, h = room['bbox']
            cropped = img_cv[y-200:y+h+200, x-200:x+w+200]  # Ampliar el área
            if cropped.size == 0:
                continue
            image_pil = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
            buf = io.BytesIO()
            image_pil.save(buf, format='PNG')

            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=room['text'], ln=True, align='C')
            temp_img_path = os.path.join(tempfile.gettempdir(), f"room_{x}_{y}.png")
            image_pil.save(temp_img_path)
            pdf.image(temp_img_path, x=10, y=20, w=180)

        out_pdf_path = os.path.join(tempfile.gettempdir(), "salas_extraidas.pdf")
        pdf.output(out_pdf_path)
        with open(out_pdf_path, "rb") as f:
            st.download_button("Descargar PDF con Salas", f, file_name="salas_extraidas.pdf")

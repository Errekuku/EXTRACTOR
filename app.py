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

st.title("Extractor de Salas desde Plano PDF (Básico)")
st.markdown("Esta es una versión básica que identifica texto 'SALA' o 'SUP M2' y extrae recortes.")

uploaded_file = st.file_uploader("Sube el plano en PDF", type=["pdf"])

if uploaded_file:
    st.success("PDF cargado correctamente. Procesando...")

    # Guardar PDF temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(uploaded_file.read())
        tmp_pdf_path = tmp_pdf.name

    try:
        # Leer PDF
        doc = fitz.open(tmp_pdf_path)
        page = doc.load_page(0)
        zoom = 2  # Reducir el zoom inicial para evitar imágenes demasiado grandes
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
            st.warning("No se detectaron salas (basado en el texto). Asegúrate de que el plano contenga nombres visibles.")
        else:
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            scale_factor = 0.2  # Ajustar el factor de escala

            for room in rooms:
                x, y, w, h = room['bbox']
                padding = 100  # Reducir el padding
                cropped = img_cv[max(0, y - padding):y + h + padding, max(0, x - padding):x + w + padding]
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

                # Ajustar las dimensiones de la imagen en el PDF
                width_mm = image_pil.width * scale_factor
                height_mm = image_pil.height * scale_factor

                # Centrar la imagen en la página
                page_width = 210
                page_height = 297
                x_pos = (page_width - width_mm) / 2
                y_pos = 30

                pdf.image(temp_img_path, x=x_pos, y=y_pos, w=width_mm)
                os.remove(temp_img_path) # Limpiar el archivo temporal

            out_pdf_path = os.path.join(tempfile.gettempdir(), "salas_extraidas.pdf")
            pdf.output(out_pdf_path)
            with open(out_pdf_path, "rb") as f:
                st.download_button("Descargar PDF con Recortes de Salas (Básico)", f, file_name="salas_extraidas.pdf")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el PDF: {e}")
    finally:
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)
        pdf.output(out_pdf_path)
        with open(out_pdf_path, "rb") as f:
            st.download_button("Descargar PDF con Salas", f, file_name="salas_extraidas.pdf")

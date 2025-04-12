import streamlit as st
import shutil
from PIL import Image
from fpdf import FPDF
import tempfile
import os

# Configura o caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

def ocr_image(image):
    return pytesseract.image_to_string(image, lang='por')

def generate_pdf(text, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    pdf.output(filename)

def main():
    st.title("Corretor de Provas com OCR")
    uploaded_file = st.file_uploader("Envie a imagem ou PDF da prova", type=["png", "jpg", "jpeg", "pdf"])

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        if uploaded_file.type == "application/pdf":
            from pdf2image import convert_from_path
            images = convert_from_path(tmp_file_path)
            text = ""
            for img in images:
                text += ocr_image(img)
        else:
            image = Image.open(tmp_file_path)
            text = ocr_image(image)

        st.text_area("Texto extraído:", text, height=300)

        if st.button("Gerar PDF"):
            output_pdf = "relatorio.pdf"
            generate_pdf(text, output_pdf)
            with open(output_pdf, "rb") as file:
                btn = st.download_button(
                    label="Baixar relatório em PDF",
                    data=file,
                    file_name=output_pdf,
                    mime="application/pdf"
                )

if _name_ == "_main_":
    main()

import streamlit as st
import pytesseract
import shutil
from pdf2image import convert_from_path
from PIL import Image
import os
from fpdf import FPDF

# Configurar o caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

# Função para extrair texto de uma imagem
def extrair_texto_imagem(imagem):
    return pytesseract.image_to_string(imagem, lang='por')

# Função para extrair texto de um PDF
def extrair_texto_pdf(pdf_path):
    imagens = convert_from_path(pdf_path)
    texto_total = ""
    for imagem in imagens:
        texto_total += pytesseract.image_to_string(imagem, lang='por')
    return texto_total

# Classe PDF com suporte a UTF-8
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", size=12)
        self.cell(0, 10, "Texto Extraído", ln=True, align="C")

    def add_text(self, texto):
        self.set_font("Arial", size=12)
        for linha in texto.split("\n"):
            try:
                self.cell(200, 10, txt=linha.encode('latin-1', 'replace').decode('latin-1'), ln=True)
            except:
                self.cell(200, 10, txt="(linha não suportada)", ln=True)

# Interface do Streamlit
def main():
    st.title("Corretor AI")

    arquivo = st.file_uploader("Faça upload de um arquivo PDF ou imagem", type=["pdf", "png", "jpg", "jpeg"])

    if arquivo is not None:
        nome_arquivo = arquivo.name
        os.makedirs("temp", exist_ok=True)
        caminho_arquivo = os.path.join("temp", nome_arquivo)

        with open(caminho_arquivo, "wb") as f:
            f.write(arquivo.getbuffer())

        if nome_arquivo.lower().endswith(".pdf"):
            texto_extraido = extrair_texto_pdf(caminho_arquivo)
        else:
            imagem = Image.open(caminho_arquivo)
            texto_extraido = extrair_texto_imagem(imagem)

        st.subheader("Texto Extraído:")
        st.text_area("", texto_extraido, height=300)

        if st.button("Download do Texto em PDF"):
            pdf = PDF()
            pdf.add_page()
            pdf.add_text(texto_extraido)
            caminho_pdf = os.path.join("temp", "texto_extraido.pdf")
            pdf.output(caminho_pdf)
            with open(caminho_pdf, "rb") as f:
                st.download_button("Clique para baixar", f, file_name="texto_extraido.pdf")

        # Limpeza
        os.remove(caminho_arquivo)
        if os.path.exists("temp/texto_extraido.pdf"):
            os.remove("temp/texto_extraido.pdf")

if __name__ == "__main__":
    main()

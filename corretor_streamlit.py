import streamlit as st
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Corretor IA", layout="centered")
st.title("Corretor de Provas com IA")

# === Funções de OCR ===
def ocr_image(image):
    return pytesseract.image_to_string(image, lang="por")

def ocr_pdf(file):
    text = ""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in doc:
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text += ocr_image(img) + "\n"
    return text

def normalize(text):
    return ''.join(e.lower() for e in text if e.isalnum() or e.isspace()).strip()

def corrigir_resposta(resposta, gabarito):
    partes = gabarito.split(";")
    total = len(partes)
    score = 0.0
    for parte in partes:
        if normalize(parte) in normalize(resposta):
            score += 1 / total
    return round(score, 2)

# === Upload do Gabarito ===
st.subheader("1. Envie o Gabarito")
gabarito_file = st.file_uploader("Gabarito (PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"])

# === Upload das Provas dos Alunos ===
st.subheader("2. Envie as Provas dos Alunos")
aluno_files = st.file_uploader("Arquivos dos Alunos (vários PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)

# === Processo de Correção ===
if gabarito_file and aluno_files:
    with st.spinner("Lendo gabarito..."):
        if gabarito_file.name.endswith(".pdf"):
            gabarito_text = ocr_pdf(gabarito_file)
        else:
            gabarito_text = ocr_image(Image.open(gabarito_file))

    st.success("Gabarito lido com sucesso!")
    st.text_area("Texto do Gabarito (separar partes com `;`)", value=gabarito_text, height=150, key="gabarito_area")

    st.subheader("3. Resultados:")
    for idx, aluno_file in enumerate(aluno_files):
        nome_aluno = aluno_file.name.rsplit(".", 1)[0]

        if aluno_file.name.endswith(".pdf"):
            resposta_text = ocr_pdf(aluno_file)
        else:
            resposta_text = ocr_image(Image.open(aluno_file))

        nota = corrigir_resposta(resposta_text, gabarito_text)
        status = "Aprovado" if nota >= 0.6 else "Reprovado"

        st.markdown(f"**{idx+1}. {nome_aluno}** — Nota: `{nota * 10:.1f}` — **{status}**")
        with st.expander("Ver resposta extraída do aluno"):
            st.text(resposta_text)

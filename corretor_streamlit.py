import streamlit as st
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import difflib
import re

st.set_page_config(page_title="Corretor IA", layout="centered")
st.title("Corretor de Provas com IA — Correção por Etapas")

# Função para extrair texto de imagens
def ocr_image(image):
    return pytesseract.image_to_string(image, lang="por")

# Função para extrair texto de PDFs
def ocr_pdf(file):
    text = ""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text

# Função para normalizar texto
def normalize(text):
    return ''.join(e.lower() for e in text if e.isalnum() or e.isspace()).strip()

# Função para comparar respostas com tolerância
def compare_responses(resposta, gabarito):
    resposta_norm = normalize(resposta)
    gabarito_norm = normalize(gabarito)
    similarity = difflib.SequenceMatcher(None, resposta_norm, gabarito_norm).ratio()
    return similarity >= 0.85  # Aceita 85% de similaridade

# Função para processar o gabarito
def process_gabarito(text):
    questoes = {}
    lines = text.strip().split('\n')
    current_q = ""
    for line in lines:
        if line.startswith("Q"):
            current_q = line.strip(":")
            questoes[current_q] = []
        elif "=" in line:
            partes = line.split("=")
            if len(partes) == 2:
                conteudo = partes[0].strip()
                peso = float(partes[1].strip())
                questoes[current_q].append((conteudo, peso))
    return questoes

# Upload do gabarito
st.subheader("1. Envie o Gabarito (PDF estruturado)")
gabarito_file = st.file_uploader("Gabarito", type=["pdf"])

# Upload das provas dos alunos
st.subheader("2. Envie as Provas dos Alunos (imagens ou PDFs)")
aluno_files = st.file_uploader("Provas dos Alunos", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)

if gabarito_file and aluno_files:
    gabarito_text = ocr_pdf(gabarito_file)
    questoes = process_gabarito(gabarito_text)

    st.success("Gabarito processado com sucesso!")

    st.subheader("3. Resultados")

    for idx, aluno_file in enumerate(aluno_files):
        nome_aluno = aluno_file.name.split(".")[0]

        if aluno_file.name.endswith(".pdf"):
            resposta_text = ocr_pdf(aluno_file)
        else:
            resposta_text = ocr_image(Image.open(aluno_file))

        nota_total = 0.0
        nota_maxima = 0.0

        for q, etapas in questoes.items():
            for etapa_texto, peso in etapas:
                if compare_responses(resposta_text, etapa_texto):
                    nota_total += peso
                nota_maxima += peso

        nota_final = (nota_total / nota_maxima) * 10 if nota_maxima > 0 else 0
        status = "Aprovado" if nota_final >= 6 else "Reprovado"

        st.markdown(f"**{idx+1}. {nome_aluno}** — Nota: `{nota_final:.1f}` — **{status}**")
        with st.expander("Ver resposta extraída"):
            st.text(resposta_text)

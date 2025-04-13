import os
import re
import streamlit as st
import fitz  # PyMuPDF
import base64
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
from fpdf import FPDF
from datetime import datetime
import easyocr

# ========== CONFIGURAÇÃO ==========
reader = easyocr.Reader(['pt', 'en'])  # Inicializa o OCR

st.set_page_config(page_title="Corretor de Provas com IA", layout="wide")
st.title("🧠 Corretor de Provas com Mathpix (via EasyOCR)")
st.subheader("Corrija provas automaticamente com base em um gabarito e imagens dos alunos.")

# ========== FUNÇÕES ==========

def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_weights_from_gabarito(file):
    if file.name.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file)
    else:
        image = Image.open(file)
        raw_text = "\n".join([line[1] for line in reader.readtext(image)])

    pesos = {}
    for match in re.finditer(r"(Q\d+)[^\n]*?= (\d+(\.\d+)?)", raw_text):
        questao = match.group(1)
        peso = float(match.group(2))
        pesos.setdefault(questao, []).append(peso)
    return raw_text, pesos

def process_images(images, gabarito_text, pesos):
    resultados = []
    for img in images:
        texto_ocr = "\n".join([line[1] for line in reader.readtext(img)])
        nota = 0
        for questao, valores in pesos.items():
            if questao in texto_ocr:
                nota += sum(valores)
        resultados.append({"Aluno": img.name, "Nota": round(nota, 2)})
    return resultados

def gerar_pdf(resultados, nome_turma, nome_professor, data_prova):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório - {nome_turma}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Professor: {nome_professor} - Data: {data_prova}", ln=True, align='C')
    pdf.ln(10)
    for r in resultados:
        pdf.cell(200, 10, txt=f"{r['Aluno']}: {r['Nota']} pontos", ln=True)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

# ========== INTERFACE ==========

with st.sidebar:
    st.header("Informações da Prova")
    nome_professor = st.text_input("Nome do Professor")
    nome_turma = st.text_input("Nome da Turma")
    data_prova = st.date_input("Data da Prova", datetime.today())
    gabarito_file = st.file_uploader("Envie o Gabarito (PDF ou imagem)", type=["pdf", "jpg", "jpeg", "png"])

st.markdown("---")
st.header("Upload das Provas dos Alunos")
uploaded_files = st.file_uploader("Selecione as imagens das provas (JPG ou PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# ========== AÇÃO ==========
if st.button("Corrigir Provas"):
    if not gabarito_file or not uploaded_files:
        st.warning("Por favor, envie o gabarito e as provas dos alunos.")
    else:
        with st.spinner("Processando o gabarito..."):
            gabarito_text, pesos = extract_weights_from_gabarito(gabarito_file)

        st.text("Pesos identificados no gabarito:")
        st.json(pesos)

        with st.spinner("Corrigindo provas dos alunos..."):
            resultados = process_images(uploaded_files, gabarito_text, pesos)

        df = pd.DataFrame(resultados)
        st.success("Correção concluída!")
        st.dataframe(df)

        st.subheader("Gráfico de Desempenho")
        fig, ax = plt.subplots()
        ax.bar(df['Aluno'], df['Nota'], color='skyblue')
        plt.xticks(rotation=90)
        st.pyplot(fig)

        st.subheader("Baixar Relatórios")
        pdf_data = gerar_pdf(resultados, nome_turma, nome_professor, data_prova)
        st.download_button("Baixar PDF", data=pdf_data, file_name="relatorio.pdf", mime="application/pdf")

        excel_output = BytesIO()
        df.to_excel(excel_output, index=False)
        st.download_button("Baixar Excel", data=excel_output.getvalue(), file_name="relatorio_notas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

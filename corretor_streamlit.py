import os
import base64
import streamlit as st
import requests
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pdfplumber
import re

# Mathpix Credentials
APP_ID = "mathmindia_ea58bf"
APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"

# Função de OCR com Mathpix
def mathpix_ocr(image_bytes):
    headers = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes}",
        "formats": ["latex_styled"]
    }
    response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers)
    return response.json().get("latex_styled", "")

# Extrai o gabarito do PDF com pesos
def extrair_gabarito_com_pesos(pdf_file):
    gabarito = {}
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            questoes = re.findall(r'(Q\d+):\s*(.*?)\n(?=Q\d+:|$)', text, re.DOTALL)
            for q, conteudo in questoes:
                etapas = re.findall(r'(.+?)\s*=\s*([\d.]+)', conteudo)
                gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

# Interface
st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("🧮 Corretor de Provas com Mathpix (notas parciais)")

col1, col2, col3 = st.columns(3)
with col1:
    nome_professor = st.text_input("Nome do Professor")
with col2:
    nome_turma = st.text_input("Turma")
with col3:
    data_prova = st.date_input("Data da Prova", datetime.today())

st.header("1. Enviar Gabarito (PDF com pesos)")
gabarito_pdf = st.file_uploader("Gabarito", type=["pdf"])

st.header("2. Enviar Imagens das Provas dos Alunos")
uploaded_files = st.file_uploader("Imagens dos Alunos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Corrigir Provas"):
    if not gabarito_pdf or not uploaded_files:
        st.error("Por favor, envie o gabarito e as provas dos alunos.")
    else:
        st.info("Extraindo gabarito com pesos...")
        gabarito = extrair_gabarito_com_pesos(gabarito_pdf)

        st.info("Processando provas com Mathpix...")
        resultados = []
        for img in uploaded_files:
            image = Image.open(img)
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            resposta_aluno = mathpix_ocr(img_str)

            aluno_nome = img.name.split(".")[0]
            resultado = {"Aluno": aluno_nome}
            nota_total = 0

            for q, etapas in gabarito.items():
                nota_q = 0
                for etapa, peso in etapas:
                    if etapa in resposta_aluno:
                        nota_q += peso
                resultado[q] = round(nota_q, 2)
                nota_total += nota_q

            resultado["Nota Total"] = round(nota_total, 2)
            resultado["Status"] = "Aprovado" if nota_total >= 6 else "Reprovado"
            resultados.append(resultado)

        df = pd.DataFrame(resultados)

        st.success("Correção concluída!")
        st.subheader("Notas dos Alunos")
        st.dataframe(df)

        # Gráfico
        st.subheader("Gráfico de Desempenho")
        fig, ax = plt.subplots()
        ax.bar(df["Aluno"], df["Nota Total"], color='skyblue')
        plt.xticks(rotation=90)
        st.pyplot(fig)

        # Excel
        st.subheader("Download da Planilha Excel")
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        st.download_button("Baixar Excel", excel_buffer.getvalue(), file_name="notas_alunos.xlsx")

        # PDF
        st.subheader("Relatório em PDF")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Relatório de Notas - {nome_turma}", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Professor: {nome_professor} - Data: {data_prova}", ln=True, align='C')
        pdf.ln(10)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=f"{row['Aluno']}: {row['Nota Total']} ({row['Status']})", ln=True)
        pdf_out = BytesIO()
        pdf.output(pdf_out)
        st.download_button("Baixar PDF", data=pdf_out.getvalue(), file_name="relatorio.pdf", mime="application/pdf")

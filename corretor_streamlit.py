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

# Configurações iniciais
st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("🧮 Corretor de Provas com Mathpix")

# Função para chamar a API do Mathpix
def mathpix_ocr(image_bytes):
    app_id = os.getenv("MATHPIX_APP_ID")
    app_key = os.getenv("MATHPIX_APP_KEY")
    headers = {
        "app_id": app_id,
        "app_key": app_key,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes}",
        "formats": ["latex_styled"]
    }
    response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers)
    return response.json()

# Função para processar imagens e extrair LaTeX
def process_images(images):
    results = []
    for img in images:
        image = Image.open(img)
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        ocr_result = mathpix_ocr(img_str)
        latex = ocr_result.get("latex_styled", "")
        results.append((img.name, latex))
    return results

# Upload do gabarito
st.sidebar.header("Configurações da Prova")
nome_professor = st.sidebar.text_input("Nome do Professor")
nome_turma = st.sidebar.text_input("Nome da Turma")
data_prova = st.sidebar.date_input("Data da Prova", datetime.today())
gabarito_file = st.sidebar.file_uploader("Upload do Gabarito (imagem)", type=["jpg", "png", "jpeg"])

# Upload das provas dos alunos
st.header("Upload das Provas dos Alunos")
uploaded_files = st.file_uploader("Selecione as imagens das provas", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if st.button("Iniciar Correção"):
    if gabarito_file and uploaded_files:
        st.info("Processando o gabarito...")
        gabarito_image = Image.open(gabarito_file)
        buffered = BytesIO()
        gabarito_image.save(buffered, format="JPEG")
        gabarito_str = base64.b64encode(buffered.getvalue()).decode()
        gabarito_latex = mathpix_ocr(gabarito_str).get("latex_styled", "")

        st.info("Processando as provas dos alunos...")
        resultados = process_images(uploaded_files)

        # Comparação e cálculo de notas (simplificado)
        notas = []
        for nome_arquivo, latex in resultados:
            nota = 1.0 if latex.strip() == gabarito_latex.strip() else 0.0
            notas.append({"Aluno": nome_arquivo, "Nota": nota})

        df_notas = pd.DataFrame(notas)

        # Exibição dos resultados
        st.subheader("Resultados")
        st.dataframe(df_notas)

        # Geração de gráfico
        st.subheader("Gráfico de Desempenho")
        fig, ax = plt.subplots()
        ax.bar(df_notas["Aluno"], df_notas["Nota"])
        plt.xticks(rotation=90)
        st.pyplot(fig)

        # Geração de relatório PDF
        st.subheader("Relatório em PDF")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Relatório de Notas - {nome_turma}", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Professor: {nome_professor} - Data: {data_prova}", ln=True, align='C')
        pdf.ln(10)
        for index, row in df_notas.iterrows():
            pdf.cell(200, 10, txt=f"{row['Aluno']}: {row['Nota']}", ln=True)
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        st.download_button("Baixar Relatório PDF", data=pdf_output.getvalue(), file_name="relatorio.pdf", mime="application/pdf")

        # Geração de planilha Excel
        st.subheader("Planilha Excel")
        excel_output = BytesIO()
        df_notas.to_excel(excel_output, index=False)
        st.download_button("Baixar Planilha Excel", data=excel_output.getvalue(), file_name="notas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.error("Por favor, faça o upload do gabarito e das provas dos alunos.")

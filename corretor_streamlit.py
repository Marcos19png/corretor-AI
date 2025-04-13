import streamlit as st
import requests
import base64
import os
import re
import io
import tempfile
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
from datetime import datetime

# ========================== CONFIGURAÇÃO ==========================
st.set_page_config(page_title="Corretor de Provas com Mathpix", layout="wide")
MATHPIX_APP_ID = "mathmindia_ea58bf"
MATHPIX_APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"

# ========================== FUNÇÕES AUXILIARES ==========================
def extrair_texto_pdf(file):
    with pdfplumber.open(file) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() + "\n"
    return texto

def extrair_gabarito(texto):
    gabarito = {}
    questoes = re.findall(r'(Q\d+)\s*(.*?)(?=Q\d+|$)', texto, re.DOTALL)
    for q, conteudo in questoes:
        etapas = re.findall(r'(.*?)=\s*([\d.]+)', conteudo.strip())
        gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

def mathpix_ocr(image_bytes):
    headers = {
        "app_id": MATHPIX_APP_ID,
        "app_key": MATHPIX_APP_KEY,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes}",
        "formats": ["latex_styled"]
    }
    response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers)
    return response.json().get("latex_styled", "")

def processar_imagens(imagens, gabarito):
    resultados = []
    textos_ocr = {}
    for img in imagens:
        nome_aluno = img.name.split(".")[0]
        image = Image.open(img)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        texto = mathpix_ocr(b64)
        textos_ocr[nome_aluno] = texto

        resultado = {"Aluno": nome_aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa in texto:
                    nota_q += peso
            resultado[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado["Nota Total"] = round(nota_total, 2)
        resultado["Status"] = "Aprovado" if nota_total >= 6 else "Reprovado"
        resultados.append(resultado)
    return resultados, textos_ocr

def gerar_pdf(resultado, turma, professor, data_prova):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Relatório - {resultado['Aluno']}", ln=True, align='C')
    pdf.cell(200, 10, f"Turma: {turma} | Professor: {professor} | Data: {data_prova}", ln=True)
    pdf.ln(10)
    for chave, valor in resultado.items():
        pdf.cell(200, 10, f"{chave}: {valor}", ln=True)
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    return pdf_output.getvalue()

def gerar_excel(resultados):
    df = pd.DataFrame(resultados)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()

def exibir_grafico(resultados):
    df = pd.DataFrame(resultados)
    fig, ax = plt.subplots()
    ax.bar(df["Aluno"], df["Nota Total"], color='skyblue')
    ax.set_ylabel("Nota")
    ax.set_title("Desempenho da Turma")
    plt.xticks(rotation=45)
    st.pyplot(fig)

# ========================== INTERFACE ==========================
st.title("🧠 Corretor de Provas com IA (Mathpix)")

with st.sidebar:
    st.header("Informações da Prova")
    professor = st.text_input("Professor")
    turma = st.text_input("Turma")
    data_prova = st.date_input("Data da Prova", datetime.today())
    gabarito_file = st.file_uploader("Gabarito (PDF ou imagem)", type=["pdf", "jpg", "jpeg", "png"])

st.subheader("Upload das Provas dos Alunos")
imagens_provas = st.file_uploader("Selecione as imagens das provas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Iniciar Correção"):
    if not gabarito_file or not imagens_provas:
        st.warning("Envie o gabarito e as provas dos alunos.")
    else:
        st.info("Extraindo gabarito...")
        if gabarito_file.name.endswith(".pdf"):
            texto_gabarito = extrair_texto_pdf(gabarito_file)
        else:
            imagem = Image.open(gabarito_file)
            buffer = io.BytesIO()
            imagem.save(buffer, format="JPEG")
            b64 = base64.b64encode(buffer.getvalue()).decode()
            texto_gabarito = mathpix_ocr(b64)

        gabarito = extrair_gabarito(texto_gabarito)
        st.success("Gabarito processado!")

        st.info("Corrigindo provas...")
        resultados, textos = processar_imagens(imagens_provas, gabarito)
        st.success("Correção concluída!")

        st.subheader("Resultados")
        df_resultado = pd.DataFrame(resultados)
        st.dataframe(df_resultado)

        exibir_grafico(resultados)

        excel_bytes = gerar_excel(resultados)
        st.download_button("Baixar Planilha Excel", data=excel_bytes, file_name="notas.xlsx")

        for r in resultados:
            pdf_bytes = gerar_pdf(r, turma, professor, data_prova)
            st.download_button(f"Baixar PDF {r['Aluno']}", data=pdf_bytes, file_name=f"{r['Aluno']}.pdf")

        with st.expander("Ver LaTeX extraído"):
            for aluno, texto in textos.items():
                st.markdown(f"**{aluno}**")
                st.code(texto, language="latex")

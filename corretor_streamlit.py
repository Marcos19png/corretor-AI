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

# Configuração da API Mathpix
MATHPIX_APP_ID = "mathmindia_ea58bf"
MATHPIX_APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"

# Página do app
st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("🧠 Corretor de Provas com Mathpix")

# Função para enviar imagem à API Mathpix
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

# Extrai gabarito de um PDF com pesos
def extrair_gabarito_pdf(pdf_file):
    gabarito = {}
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            questoes = re.findall(r'(Q\d+)([\s\S]*?)(?=Q\d+|$)', texto)
            for q, bloco in questoes:
                etapas = re.findall(r'(.+?)=\s*([\d.]+)', bloco.strip())
                gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

# Extrai LaTeX de imagens via Mathpix
def imagem_para_latex(imagem):
    image = Image.open(imagem)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return mathpix_ocr(img_str)

# Compara etapas com base em similaridade
def etapa_correspondente(etapa_gabarito, texto_aluno):
    return etapa_gabarito.strip() in texto_aluno

# Processa as provas
def processar_provas(arquivos_imagem, gabarito):
    resultados = []
    textos_ocr = {}
    for img in arquivos_imagem:
        latex = imagem_para_latex(img)
        aluno = os.path.splitext(img.name)[0]
        textos_ocr[aluno] = latex
        resultado = {'Aluno': aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa_correspondente(etapa, latex):
                    nota_q += peso
            resultado[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado['Nota Total'] = round(nota_total, 2)
        resultado['Status'] = 'Aprovado' if nota_total >= 6.0 else 'Reprovado'
        resultados.append(resultado)
    return resultados, textos_ocr

# Gerar PDF geral
def gerar_pdf_geral(resultados, professor, turma, data_prova):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório de Notas - {turma}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Professor: {professor} - Data: {data_prova}", ln=True, align='C')
    pdf.ln(10)
    for r in resultados:
        linha = f"{r['Aluno']}: Nota = {r['Nota Total']} - {r['Status']}"
        pdf.cell(200, 10, txt=linha, ln=True)
    output = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
return pdf_bytes

# Gráfico de desempenho
def plotar_grafico(resultados):
    df = pd.DataFrame(resultados)
    fig, ax = plt.subplots()
    ax.bar(df['Aluno'], df['Nota Total'], color='skyblue')
    plt.xticks(rotation=90)
    st.pyplot(fig)

# Sidebar - dados da prova
st.sidebar.header("Informações da Prova")
professor = st.sidebar.text_input("Nome do Professor")
turma = st.sidebar.text_input("Nome da Turma")
data_prova = st.sidebar.date_input("Data da Prova", datetime.today())
gabarito_file = st.sidebar.file_uploader("Gabarito (PDF ou imagem)", type=["pdf", "jpg", "jpeg", "png"])

# Upload das provas dos alunos
st.header("Upload das Provas dos Alunos")
arquivos_imagem = st.file_uploader("Selecionar imagens das provas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Iniciar Correção"):
    if gabarito_file and arquivos_imagem:
        st.info("Extraindo gabarito...")
        if gabarito_file.type == "application/pdf":
            gabarito = extrair_gabarito_pdf(gabarito_file)
        else:
            latex_gabarito = imagem_para_latex(gabarito_file)
            gabarito = {"Q1": [(latex_gabarito, 1.0)]}  # Default

        st.info("Corrigindo provas...")
        resultados, textos_ocr = processar_provas(arquivos_imagem, gabarito)

        st.success("Correção concluída!")
        st.subheader("Notas dos Alunos")
        st.dataframe(pd.DataFrame(resultados))

        st.subheader("Gráfico de Desempenho")
        plotar_grafico(resultados)

        st.subheader("Baixar Relatórios")
        excel = BytesIO()
        pd.DataFrame(resultados).to_excel(excel, index=False)
        st.download_button("Baixar Excel", data=excel.getvalue(), file_name="notas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        pdf_bytes = gerar_pdf_geral(resultados, professor, turma, data_prova)
        st.download_button("Baixar PDF Geral", data=pdf_bytes, file_name="relatorio.pdf", mime="application/pdf")

        with st.expander("LaTeX Extraído das Provas"):
            for aluno, latex in textos_ocr.items():
                st.markdown(f"**{aluno}**")
                st.latex(latex)
    else:
        st.warning("Envie o gabarito e as provas dos alunos.")

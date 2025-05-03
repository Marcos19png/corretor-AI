import os
import base64
import streamlit as st
import requests
from PIL import Image, ImageEnhance
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pdfplumber
import re
from sympy import simplify
from sympy.parsing.latex import parse_latex

# ========== CONFIGURAÇÃO MATHPIX ==========
MATHPIX_APP_ID = "mathmindia_ea58bf"
MATHPIX_APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"

# ========== STREAMLIT ==========
st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("🧠 Corretor de Provas com Mathpix + SymPy")

# ========== FUNÇÕES ==========
def mathpix_ocr(image_bytes):
    headers = {
        "app_id": MATHPIX_APP_ID,
        "app_key": MATHPIX_APP_KEY,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes}",
        "formats": ["latex_styled"],
        "math_inline_delimiters": ["\\(", "\\)"],
        "skip_recrop": True
    }
    response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers)
    return response.json().get("latex_styled", "")

def imagem_para_latex(imagem):
    image = Image.open(imagem).convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return mathpix_ocr(img_str)

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

def extrair_expressoes(latex_text):
    # Extrai expressões dentro de \( \)
    expressoes = re.findall(r'\\\((.*?)\\\)', latex_text)

    # Extrai de blocos \begin{array}
    arrays = re.findall(r'\\begin{array}{.*?}(.*?)\\end{array}', latex_text, re.DOTALL)
    for bloco in arrays:
        linhas = bloco.split(r'\\')
        for linha in linhas:
            linha = linha.strip()
            if '=' in linha:
                expressoes.append(linha)
    
    return expressoes

def etapa_correspondente(etapa_gabarito, latex_text):
    try:
        gabarito_expr = parse_latex(etapa_gabarito)
    except:
        return False

    expressoes = extrair_expressoes(latex_text)

    for exp in expressoes:
        try:
            aluno_expr = parse_latex(exp)
            if simplify(gabarito_expr - aluno_expr) == 0:
                return True
        except:
            continue
    return False

def processar_provas(imagens, gabarito):
    resultados = []
    textos_ocr = {}
    for img in imagens:
        latex = imagem_para_latex(img)
        aluno = os.path.splitext(img.name)[0]
        textos_ocr[aluno] = latex
        resultado = {"Aluno": aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa_correspondente(etapa, latex):
                    nota_q += peso
            resultado[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado["Nota Total"] = round(nota_total, 2)
        resultado["Status"] = "Aprovado" if nota_total >= 6.0 else "Reprovado"
        resultados.append(resultado)
    return resultados, textos_ocr

def gerar_pdf_geral(resultados, professor, turma, data_prova):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório de Notas - {turma}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Professor: {professor} - Data: {data_prova}", ln=True, align='C')
    pdf.ln(10)
    for r in resultados:
        pdf.cell(200, 10, txt=f"{r['Aluno']}: Nota = {r['Nota Total']} - {r['Status']}", ln=True)
    return pdf.output(dest="S").encode("latin1")

def plotar_grafico(resultados):
    df = pd.DataFrame(resultados)
    fig, ax = plt.subplots()
    ax.bar(df["Aluno"], df["Nota Total"], color="skyblue")
    plt.xticks(rotation=90)
    st.pyplot(fig)

# ========== INTERFACE ==========
st.sidebar.header("Informações da Prova")
professor = st.sidebar.text_input("Nome do Professor")
turma = st.sidebar.text_input("Nome da Turma")
data_prova = st.sidebar.date_input("Data da Prova", datetime.today())
gabarito_file = st.sidebar.file_uploader("Gabarito (PDF ou Imagem)", type=["pdf", "jpg", "jpeg", "png"])

st.header("Upload das Provas dos Alunos")
arquivos_imagem = st.file_uploader("Selecionar imagens das provas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Iniciar Correção"):
    if gabarito_file and arquivos_imagem:
        st.info("Extraindo gabarito...")
        if gabarito_file.type == "application/pdf":
            gabarito = extrair_gabarito_pdf(gabarito_file)
        else:
            latex = imagem_para_latex(gabarito_file)
            gabarito = {"Q1": [(latex, 1.0)]}

        st.info("Corrigindo provas...")
        resultados, textos = processar_provas(arquivos_imagem, gabarito)

        st.success("Correção concluída!")
        st.dataframe(pd.DataFrame(resultados))
        plotar_grafico(resultados)

        st.subheader("Relatórios")
        excel = BytesIO()
        pd.DataFrame(resultados).to_excel(excel, index=False)
        st.download_button("Baixar Excel", data=excel.getvalue(), file_name="notas.xlsx")

        pdf = gerar_pdf_geral(resultados, professor, turma, data_prova)
        st.download_button("Baixar PDF", data=pdf, file_name="relatorio.pdf")

        with st.expander("LaTeX Detectado"):
            for aluno, latex in textos.items():
                st.markdown(f"**{aluno}**")
                st.code(latex)
    else:
        st.warning("Envie o gabarito e as imagens das provas.")

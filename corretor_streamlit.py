import os
import base64
import streamlit as st
import requests
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pdfplumber
import re
import json
from sympy import simplify
from sympy.parsing.latex import parse_latex

# ========== CONFIG MATHPIX ==========
MATHPIX_APP_ID = "mathmindia_ea58bf"
MATHPIX_APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"
CACHE_FILE = "latex_cache.json"

# ========== FUNÇÕES ==========
def carregar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def salvar_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

latex_cache = carregar_cache()

def preprocess_image(image):
    img = Image.open(image).convert("L")
    img = ImageOps.autocontrast(img)
    img = img.resize((min(img.size[0], 1500), min(img.size[1], 2000)))
    enhancer = ImageEnhance.Sharpness(img)
    return enhancer.enhance(2.0)

def image_to_base64(img):
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()

def mathpix_ocr(image_bytes_b64):
    headers = {
        "app_id": MATHPIX_APP_ID,
        "app_key": MATHPIX_APP_KEY,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes_b64}",
        "formats": ["latex_styled"]
    }
    try:
        r = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers)
        if r.status_code == 200:
            return r.json().get("latex_styled", "")
    except:
        pass
    return ""

def fallback_ocr_pytesseract(image):
    return pytesseract.image_to_string(image)

def avaliar_confianca_latex(latex):
    if len(latex) < 10 or "=" not in latex:
        return "baixa"
    return "alta"

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

def etapa_correspondente(etapa_gabarito, latex_text):
    try:
        expr_gab = parse_latex(etapa_gabarito)
    except:
        return False
    expressoes = re.findall(r'(\\\(.+?\\\))', latex_text)
    for exp in expressoes:
        clean = exp.strip('\\() ')
        try:
            expr_aluno = parse_latex(clean)
            if simplify(expr_gab - expr_aluno) == 0:
                return True
        except:
            continue
    return False

def imagem_para_latex(imagem, aluno_nome):
    img = preprocess_image(imagem)
    b64 = image_to_base64(img)

    if aluno_nome in latex_cache:
        return latex_cache[aluno_nome], "alta (cache)"

    latex = mathpix_ocr(b64)
    confianca = avaliar_confianca_latex(latex)

    if not latex:
        st.warning(f"Mathpix falhou. Usando fallback com OCR padrão para {aluno_nome}.")
        latex = fallback_ocr_pytesseract(img)
        confianca = "baixa (fallback)"

    if confianca == "baixa":
        st.warning(f"Baixa confiança no LaTeX de {aluno_nome}. Reveja e edite abaixo:")
        st.image(img, caption="Imagem da prova")
        latex = st.text_area(f"LaTeX detectado para {aluno_nome}:", value=latex)

    latex_cache[aluno_nome] = latex
    salvar_cache(latex_cache)
    return latex, confianca

def processar_provas(imagens, gabarito):
    resultados = []
    latex_detectados = {}
    for img in imagens:
        aluno = os.path.splitext(img.name)[0]
        latex, confianca = imagem_para_latex(img, aluno)
        latex_detectados[aluno] = {"latex": latex, "confianca": confianca}

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
    return resultados, latex_detectados

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

# ========== INTERFACE STREAMLIT ==========
st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("🧠 Corretor de Provas com Mathpix + SymPy")

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
            latex, _ = imagem_para_latex(gabarito_file, "gabarito")
            gabarito = {"Q1": [(latex, 1.0)]}

        st.info("Corrigindo provas...")
        resultados, latex_detectados = processar_provas(arquivos_imagem, gabarito)

        st.success("Correção concluída!")
        st.dataframe(pd.DataFrame(resultados))
        plotar_grafico(resultados)

        st.subheader("Relatórios")
        excel = BytesIO()
        pd.DataFrame(resultados).to_excel(excel, index=False)
        st.download_button("Baixar Excel", data=excel.getvalue(), file_name="notas.xlsx")

        pdf = gerar_pdf_geral(resultados, professor, turma, data_prova)
        st.download_button("Baixar PDF", data=pdf, file_name="relatorio.pdf")

        st.subheader("LaTeX Detectado por Aluno")
        for aluno, info in latex_detectados.items():
            st.markdown(f"**{aluno}** (Confiança: {info['confianca']})")
            st.code(info["latex"])
    else:
        st.warning("Envie o gabarito e as imagens das provas.")

import os
import base64
import streamlit as st
import requests
from PIL import Image, ImageOps, ImageEnhance
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pdfplumber
import re
from sympy import simplify
from sympy.parsing.latex import parse_latex
import pytesseract

# ========== CONFIG ==========
MATHPIX_APP_ID = "mathmindia_ea58bf"
MATHPIX_APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"

st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("🧠 Corretor de Provas com Mathpix + SymPy")

# ========== FUNÇÕES ==========

def preprocess_image(image_file):
    image = Image.open(image_file).convert("L")
    image = ImageOps.invert(image)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = image.resize((int(image.width * 1.5), int(image.height * 1.5)))
    return image

def image_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()

def mathpix_ocr(image_bytes):
    headers = {
        "app_id": MATHPIX_APP_ID,
        "app_key": MATHPIX_APP_KEY,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes}",
        "formats": ["latex_styled", "text"],
        "ocr": ["math", "text"],
        "snip_format": "latex"
    }
    try:
        response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers, timeout=20)
        result = response.json()
        latex = result.get("latex_styled", "")
        if latex and len(latex) > 10:
            return latex, False
        raise ValueError("LaTeX inválido ou vazio")
    except Exception:
        return pytesseract.image_to_string(Image.open(BytesIO(base64.b64decode(image_bytes)))), True

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
        gabarito_expr = parse_latex(etapa_gabarito)
    except Exception:
        return False

    expressoes = re.findall(r'(\\\(.+?\\\))', latex_text)
    for exp in expressoes:
        clean = exp.strip('\\() ')
        try:
            aluno_expr = parse_latex(clean)
            if simplify(gabarito_expr - aluno_expr) == 0:
                return True
        except Exception:
            continue
    return False

def processar_provas(imagens, gabarito):
    resultados = []
    textos_ocr = {}
    for img in imagens:
        imagem_proc = preprocess_image(img)
        img_base64 = image_to_base64(imagem_proc)
        latex, fallback = mathpix_ocr(img_base64)

        aluno = os.path.splitext(img.name)[0]
        textos_ocr[aluno] = (latex, fallback)
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
gabarito_file = st.sidebar.file_uploader("Gabarito (PDF)", type=["pdf"])

st.header("Upload das Provas dos Alunos")
arquivos_imagem = st.file_uploader("Selecionar imagens das provas", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Iniciar Correção"):
    if gabarito_file and arquivos_imagem:
        st.info("Extraindo gabarito...")
        gabarito = extrair_gabarito_pdf(gabarito_file)

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

        with st.expander("LaTeX Detectado por Aluno"):
            for aluno, (latex, fallback) in textos.items():
                st.markdown(f"**{aluno}** — {'Fallback OCR' if fallback else 'Mathpix'}")
                st.code(latex)
    else:
        st.warning("Envie o gabarito e as imagens das provas.")

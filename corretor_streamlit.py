import streamlit as st
import pytesseract
import shutil
from PIL import Image
import pdfplumber
import io
import re
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
import difflib
import unicodedata

# Configuração do Tesseract
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    st.warning("Tesseract não encontrado.")

# Funções
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return ''.join(c for c in texto if not unicodedata.combining(c))

def etapa_correspondente(etapa_gabarito, texto_aluno):
    etapa_norm = normalizar(etapa_gabarito)
    texto_norm = normalizar(texto_aluno)
    return difflib.get_close_matches(etapa_norm, texto_norm.split(), n=1, cutoff=0.85)

def extrair_gabarito(file):
    gabarito = {}
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            questoes = re.findall(r'(Q\d+):\s*(.*?)\n(?=Q\d+:|$)', texto, re.DOTALL)
            for q, conteudo in questoes:
                etapas = re.findall(r'(.+?)\s*=\s*([\d.]+)', conteudo)
                gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

def processar_imagens(imagens, gabarito, nota_minima):
    resultados = []
    for imagem in imagens:
        nome_aluno = imagem.name.split(".")[0]
        texto = pytesseract.image_to_string(Image.open(imagem))
        resultado = {"Aluno": nome_aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa_correspondente(etapa, texto):
                    nota_q += peso
            resultado[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado["Nota Total"] = round(nota_total, 2)
        resultado["Status"] = "Aprovado" if nota_total >= nota_minima else "Reprovado"
        resultados.append(resultado)
    return resultados

def gerar_pdf_em_memoria(resultados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório Geral", ln=True, align='C')
    for r in resultados:
        pdf.ln(5)
        for k, v in r.items():
            pdf.cell(200, 10, txt=f"{k}: {v}", ln=True)
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

def gerar_excel_em_memoria(resultados):
    df = pd.DataFrame(resultados)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

def exibir_grafico(resultados):
    nomes = [r['Aluno'] for r in resultados]
    notas = [r['Nota Total'] for r in resultados]
    fig, ax = plt.subplots()
    ax.barh(nomes, notas, color='skyblue')
    ax.set_xlabel('Nota Total')
    ax.set_title('Desempenho dos Alunos')
    st.pyplot(fig)

# Interface
st.title("Corretor IA (sem salvar arquivos)")

nota_minima = st.number_input("Nota mínima para aprovação:", min_value=0.0, max_value=10.0, value=6.0)

gabarito_pdf = st.file_uploader("Envie o gabarito (PDF)", type="pdf")
provas = st.file_uploader("Envie provas dos alunos (imagens)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if gabarito_pdf and provas:
    gabarito = extrair_gabarito(gabarito_pdf)
    resultados = processar_imagens(provas, gabarito, nota_minima)
    st.success("Correção concluída!")

    pdf_bytes = gerar_pdf_em_memoria(resultados)
    excel_bytes = gerar_excel_em_memoria(resultados)

    st.download_button("Baixar Relatório em PDF", pdf_bytes, file_name="relatorio.pdf")
    st.download_button("Baixar Planilha Excel", excel_bytes, file_name="relatorio.xlsx")

    exibir_grafico(resultados)

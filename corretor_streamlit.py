import streamlit as st
import pytesseract
import shutil
from PIL import Image
import pdfplumber
import re
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
import difflib
import unicodedata
import io
import zipfile

# Configurar Tesseract (compatível com Streamlit Cloud)
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    st.warning("Tesseract não encontrado.")

# Normalização e comparação tolerante
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return ''.join(c for c in texto if not unicodedata.combining(c))

def etapa_correspondente(etapa_gabarito, texto_aluno):
    etapa_norm = normalizar(etapa_gabarito)
    texto_norm = normalizar(texto_aluno)
    return difflib.get_close_matches(etapa_norm, texto_norm.split(), n=1, cutoff=0.8)

# Gabarito a partir do PDF
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

# Agrupar imagens por aluno
def agrupar_imagens_por_aluno(imagens):
    agrupadas = {}
    for imagem in imagens:
        nome = imagem.name.split(".")[0]
        aluno = re.sub(r'_pag\d+', '', nome)
        agrupadas.setdefault(aluno, []).append(imagem)
    return agrupadas

# Processar imagens e calcular nota
def processar_provas(agrupadas, gabarito, nota_minima):
    resultados = []
    textos_ocr = {}
    for aluno, imagens in agrupadas.items():
        texto_completo = ''
        for img in imagens:
            texto = pytesseract.image_to_string(Image.open(img))
            texto_completo += '\n' + texto
        textos_ocr[aluno] = texto_completo

        resultado = {'Aluno': aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa_correspondente(etapa, texto_completo):
                    nota_q += peso
            resultado[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado['Nota Total'] = round(nota_total, 2)
        resultado['Status'] = 'Aprovado' if nota_total >= nota_minima else 'Reprovado'
        resultados.append(resultado)
    return resultados, textos_ocr

# Geração de PDF
def gerar_pdf_individual_em_memoria(resultado, turma, professor, data_prova):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório - {resultado['Aluno']}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Turma: {turma}", ln=True)
    pdf.cell(200, 10, txt=f"Data da prova: {data_prova}", ln=True)
    pdf.cell(200, 10, txt=f"Professor: {professor}", ln=True)
    pdf.ln(10)

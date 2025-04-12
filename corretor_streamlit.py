import streamlit as st
import pytesseract
from PIL import Image
import pdfplumber
import os
import re
import pandas as pd
from fpdf import FPDF
import difflib
import unicodedata

# === CONFIGURAÇÕES INICIAIS ===

st.set_page_config(page_title="Corretor IA", layout="centered")
st.title("Corretor de Provas com IA")

# === FUNÇÕES AUXILIARES ===

def normalizar(texto):
    """Remove acentos, símbolos e transforma em minúsculas"""
    texto = unicodedata.normalize("NFKD", texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    return texto.lower().strip()

def comparar_com_tolerancia(resposta_aluno, resposta_gabarito):
    """Compara textos com tolerância usando similaridade"""
    resposta_aluno = normalizar(resposta_aluno)
    resposta_gabarito = normalizar(resposta_gabarito)
    return difflib.SequenceMatcher(None, resposta_aluno, resposta_gabarito).ratio() >= 0.85

def extrair_gabarito(pdf_path):
    """Extrai questões e etapas com pesos de um PDF"""
    gabarito = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            questoes = re.findall(r'(Q\d+):\s*(.*?)\n(?=Q\d+:|$)', texto, re.DOTALL)
            for q, conteudo in questoes:
                etapas = re.findall(r'(.+?)\s*=\s*([\d.]+)', conteudo)
                gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

def processar_provas(imagens, gabarito):
    """Corrige cada imagem com base nas etapas do gabarito"""
    resultados = []
    for imagem in imagens:
        nome_aluno = os.path.splitext(os.path.basename(imagem.name))[0]
        imagem_pil = Image.open(imagem)
        texto = pytesseract.image_to_string(imagem_pil, lang="por")
        resultado_aluno = {'Aluno': nome_aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if comparar_com_tolerancia(texto, etapa):
                    nota_q += peso
            resultado_aluno[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado_aluno['Nota Total'] = round(nota_total, 2)
        resultado_aluno['Status'] = 'Aprovado' if nota_total >= 0.6 else 'Reprovado'
        resultados.append(resultado_aluno)
    return resultados

def gerar_pdf(resultados, pagina):
    """Cria um PDF com os resultados de todos os alunos"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório de Resultados - Página {pagina}", ln=True, align='C')
    for resultado in resultados:
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Aluno: {resultado['Aluno']}", ln=True)
        for chave, valor in resultado.items():
            if chave not in ['Aluno', 'Nota Total', 'Status']:
                pdf.cell(200, 10, txt=f"{chave}: {valor}", ln=True)
        pdf.cell(200, 10, txt=f"Nota Total: {resultado['Nota Total']}", ln=True)
        pdf.cell(200, 10, txt=f"Status: {resultado['Status']}", ln=True)
    pdf.output("relatorio_resultados.pdf")

def gerar_excel(resultados):
    """Cria uma planilha Excel com todos os resultados"""
    df = pd.DataFrame(resultados)
    df.to_excel("relatorio_resultados.xlsx", index=False)

# === INTERFACE DO USUÁRIO ===

pagina_corrente = st.text_input("Informe o número da página corrigida:", value="1")

gabarito_pdf = st.file_uploader("Envie o gabarito (PDF com estrutura de questões)", type="pdf")
imagens_provas = st.file_uploader("Envie as provas dos alunos (imagens)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if gabarito_pdf and imagens_provas:
    with st.spinner("Processando..."):
        gabarito = extrair_gabarito(gabarito_pdf)
        resultados = processar_provas(imagens_provas, gabarito)
        gerar_pdf(resultados, pagina=pagina_corrente)
        gerar_excel(resultados)

    st.success("Correção concluída!")

    # Botões de download
    with open("relatorio_resultados.pdf", "rb") as pdf_file:
        st.download_button("Baixar Relatório PDF", pdf_file, file_name=f"relatorio_pagina_{pagina_corrente}.pdf")
    with open("relatorio_resultados.xlsx", "rb") as excel_file:
        st.download_button("Baixar Planilha Excel", excel_file, file_name=f"resultados_pagina_{pagina_corrente}.xlsx")

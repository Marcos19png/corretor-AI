import streamlit as st
import pytesseract
from PIL import Image
import pdfplumber
import os
import re
import pandas as pd
from fpdf import FPDF

# Função para extrair etapas e pesos do gabarito
def extrair_gabarito(pdf_path):
    gabarito = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            questoes = re.findall(r'(Q\d+):\s*(.*?)\n(?=Q\d+:|$)', texto, re.DOTALL)
            for q, conteudo in questoes:
                etapas = re.findall(r'(.+?)\s*=\s*([\d.]+)', conteudo)
                gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

# Função para processar as imagens das provas dos alunos
def processar_provas(imagens, gabarito):
    resultados = []
    for imagem in imagens:
        nome_aluno = os.path.splitext(os.path.basename(imagem.name))[0]
        imagem_pil = Image.open(imagem)
        texto = pytesseract.image_to_string(imagem_pil)
        resultado_aluno = {'Aluno': nome_aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa in texto:
                    nota_q += peso
            resultado_aluno[q] = nota_q
            nota_total += nota_q
        resultado_aluno['Nota Total'] = nota_total
        resultado_aluno['Status'] = 'Aprovado' if nota_total >= 0.6 else 'Reprovado'
        resultados.append(resultado_aluno)
    return resultados

# Função para gerar relatório PDF
def gerar_pdf(resultados, pagina):
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

# Função para gerar planilha Excel
def gerar_excel(resultados):
    df = pd.DataFrame(resultados)
    df.to_excel("relatorio_resultados.xlsx", index=False)

# Interface do Streamlit
st.title("Corretor de Provas com IA")

gabarito_pdf = st.file_uploader("Envie o gabarito (PDF)", type="pdf")
imagens_provas = st.file_uploader("Envie as provas dos alunos (imagens)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if gabarito_pdf and imagens_provas:
    gabarito = extrair_gabarito(gabarito_pdf)
    resultados = processar_provas(imagens_provas, gabarito)
    gerar_pdf(resultados, pagina=1)
    gerar_excel(resultados)
    st.success("Correção concluída!")
    with open("relatorio_resultados.pdf", "rb") as pdf_file:
        st.download_button("Baixar Relatório PDF", pdf_file, file_name="relatorio_resultados.pdf")
    with open("relatorio_resultados.xlsx", "rb") as excel_file:
        st.download_button("Baixar Planilha Excel", excel_file, file_name="relatorio_resultados.xlsx")

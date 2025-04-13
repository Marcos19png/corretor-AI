import streamlit as st
import pytesseract
import shutil
from PIL import Image
import pdfplumber
import os
import re
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
import difflib
import unicodedata

# Detectar o caminho do Tesseract dinamicamente (compatível com nuvem e Windows)
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    st.warning("Tesseract não encontrado. Se estiver rodando localmente, instale o Tesseract OCR.")

# Criar pastas com segurança
for pasta in [
    "relatorios",
    "relatorios/pdf",
    "relatorios/excel",
    "relatorios/individuais",
    "uploads"
]:
    os.makedirs(pasta, exist_ok=True)

def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return ''.join(c for c in texto if not unicodedata.combining(c))

def etapa_correspondente(etapa_gabarito, texto_aluno):
    etapa_norm = normalizar(etapa_gabarito)
    texto_norm = normalizar(texto_aluno)
    return difflib.get_close_matches(etapa_norm, texto_norm.split(), n=1, cutoff=0.85)

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

def agrupar_imagens_por_aluno(imagens):
    agrupadas = {}
    for imagem in imagens:
        nome = os.path.splitext(imagem.name)[0]
        aluno = re.sub(r'_pag\d+', '', nome)
        agrupadas.setdefault(aluno, []).append(imagem)
    return agrupadas

def processar_provas(agrupadas, gabarito, nota_minima):
    resultados = []
    for aluno, imagens in agrupadas.items():
        texto_completo = ''
        for img in imagens:
            texto = pytesseract.image_to_string(Image.open(img))
            texto_completo += '\n' + texto
        resultado_aluno = {'Aluno': aluno}
        nota_total = 0
        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa_correspondente(etapa, texto_completo):
                    nota_q += peso
            resultado_aluno[q] = round(nota_q, 2)
            nota_total += nota_q
        resultado_aluno['Nota Total'] = round(nota_total, 2)
        resultado_aluno['Status'] = 'Aprovado' if nota_total >= nota_minima else 'Reprovado'
        resultados.append(resultado_aluno)
    return resultados

def gerar_pdf_individual(resultado, turma, professor, data_prova):
    pasta_turma = f"relatorios/individuais/{turma}"
    os.makedirs(pasta_turma, exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório - {resultado['Aluno']}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Turma: {turma}", ln=True)
    pdf.cell(200, 10, txt=f"Data da prova: {data_prova}", ln=True)
    pdf.cell(200, 10, txt=f"Professor: {professor}", ln=True)
    pdf.ln(10)
    for chave, valor in resultado.items():
        pdf.cell(200, 10, txt=f"{chave}: {valor}", ln=True)
    caminho = os.path.join(pasta_turma, f"{resultado['Aluno']}_relatorio.pdf")
    pdf.output(caminho)

def gerar_pdf_geral(resultados, turma, professor, data_prova):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Relatório Geral - Turma: {turma}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Data da prova: {data_prova}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Professor: {professor}", ln=True, align='C')
    pdf.ln(10)
    for resultado in resultados:
        for chave, valor in resultado.items():
            pdf.cell(200, 10, txt=f"{chave}: {valor}", ln=True)
        pdf.ln(5)
    pdf.output("relatorios/pdf/relatorio_geral.pdf")

def gerar_excel(resultados):
    df = pd.DataFrame(resultados)
    df.to_excel("relatorios/excel/relatorio_resultados.xlsx", index=False)

def salvar_historico(resultados):
    df_novo = pd.DataFrame(resultados)
    if os.path.exists("historico.csv"):
        df_existente = pd.read_csv("historico.csv")
        df_total = pd.concat([df_existente, df_novo], ignore_index=True)
    else:
        df_total = df_novo
    df_total.to_csv("historico.csv", index=False)

def exibir_grafico(resultados):
    nomes = [r['Aluno'] for r in resultados]
    notas = [r['Nota Total'] for r in resultados]
    fig, ax = plt.subplots()
    ax.barh(nomes, notas, color='skyblue')
    ax.set_xlabel('Nota Total')
    ax.set_title('Desempenho dos Alunos')
    st.pyplot(fig)

# Interface do usuário
st.title("Corretor de Provas com IA")

turma = st.text_input("Turma:")
professor = st.text_input("Professor:")
data_prova = st.date_input("Data da prova:")
nota_minima = st.number_input("Nota mínima para aprovação:", min_value=0.0, max_value=10.0, value=6.0, step=0.1)

gabarito_pdf = st.file_uploader("Envie o gabarito (PDF)", type="pdf")
imagens_provas = st.file_uploader("Envie as provas dos alunos (imagens)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if gabarito_pdf and imagens_provas:
    st.info("Processando correção...")

    gabarito_caminho = f"uploads/gabarito_{gabarito_pdf.name}"
    with open(gabarito_caminho, "wb") as f:
        f.write(gabarito_pdf.read())

    for imagem in imagens_provas:
        with open(f"uploads/prova_{imagem.name}", "wb") as f:
            f.write(imagem.read())

    gabarito = extrair_gabarito(gabarito_caminho)
    agrupadas = agrupar_imagens_por_aluno(imagens_provas)
    resultados = processar_provas(agrupadas, gabarito, nota_minima)

    for resultado in resultados:
        gerar_pdf_individual(resultado, turma, professor, data_prova)

    gerar_pdf_geral(resultados, turma, professor, data_prova)
    gerar_excel(resultados)
    salvar_historico(resultados)

    st.success("Correção concluída!")

    with open("relatorios/pdf/relatorio_geral.pdf", "rb") as f:
        st.download_button("Baixar Relatório Geral PDF", f, file_name="relatorio_geral.pdf")

    with open("relatorios/excel/relatorio_resultados.xlsx", "rb") as f:
        st.download_button("Baixar Planilha Excel", f, file_name="relatorio_resultados.xlsx")

    exibir_grafico(resultados)

import streamlit as st
import pytesseract
from PIL import Image
import pdfplumber
import os
import re
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
import difflib
import unicodedata

# Criar diretórios se não existirem
os.makedirs("relatorios/pdf", exist_ok=True)
os.makedirs("relatorios/excel", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Função para remover acentos e normalizar texto
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto

# Comparação com tolerância de similaridade
def etapa_correspondente(etapa_gabarito, texto_aluno):
    etapa_norm = normalizar(etapa_gabarito)
    texto_norm = normalizar(texto_aluno)
    return difflib.get_close_matches(etapa_norm, texto_norm.split(), n=1, cutoff=0.85)

# Extrair etapas e pesos do gabarito
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

# Processar imagens das provas
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
                if etapa_correspondente(etapa, texto):
                    nota_q += peso
            resultado_aluno[q] = nota_q
            nota_total += nota_q
        resultado_aluno['Nota Total'] = nota_total
        resultado_aluno['Status'] = 'Aprovado' if nota_total >= 0.6 else 'Reprovado'
        resultados.append(resultado_aluno)
    return resultados

# Gerar PDF com resultados
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
    pdf.output(f"relatorios/pdf/relatorio_resultados_pagina_{pagina}.pdf")

# Gerar planilha Excel
def gerar_excel(resultados):
    df = pd.DataFrame(resultados)
    df.to_excel("relatorios/excel/relatorio_resultados.xlsx", index=False)

# Salvar histórico geral
def salvar_historico(resultados):
    df_novo = pd.DataFrame(resultados)
    caminho_historico = "historico.csv"
    if os.path.exists(caminho_historico):
        df_existente = pd.read_csv(caminho_historico)
        df_total = pd.concat([df_existente, df_novo], ignore_index=True)
    else:
        df_total = df_novo
    df_total.to_csv(caminho_historico, index=False)

# Gráfico de desempenho
def exibir_grafico(resultados):
    nomes = [r['Aluno'] for r in resultados]
    notas = [r['Nota Total'] for r in resultados]
    fig, ax = plt.subplots()
    ax.barh(nomes, notas, color='skyblue')
    ax.set_xlabel('Nota Total')
    ax.set_title('Desempenho dos Alunos')
    st.pyplot(fig)

# Interface
st.title("Corretor de Provas com IA")

gabarito_pdf = st.file_uploader("Envie o gabarito (PDF)", type="pdf")
imagens_provas = st.file_uploader("Envie as provas dos alunos (imagens)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if gabarito_pdf and imagens_provas:
    # Salvar os arquivos
    gabarito_path = f"uploads/gabarito_{gabarito_pdf.name}"
    with open(gabarito_path, "wb") as f:
        f.write(gabarito_pdf.read())

    prova_paths = []
    for imagem in imagens_provas:
        path = f"uploads/prova_{imagem.name}"
        with open(path, "wb") as f:
            f.write(imagem.read())
        prova_paths.append(path)

    gabarito_pdf.seek(0)
    gabarito = extrair_gabarito(gabarito_pdf)
    resultados = processar_provas(imagens_provas, gabarito)

    gerar_pdf(resultados, pagina=1)
    gerar_excel(resultados)
    salvar_historico(resultados)

    st.success("Correção concluída!")

    with open("relatorios/pdf/relatorio_resultados_pagina_1.pdf", "rb") as pdf_file:
        st.download_button("Baixar Relatório PDF", pdf_file, file_name="relatorio_resultados.pdf")

    with open("relatorios/excel/relatorio_resultados.xlsx", "rb") as excel_file:
        st.download_button("Baixar Planilha Excel", excel_file, file_name="relatorio_resultados.xlsx")

    exibir_grafico(resultados)

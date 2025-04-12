import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from fpdf import FPDF
import os
import tempfile
import re

pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

# Função para extrair texto
def extrair_texto(arquivo):
    if arquivo.type == "application/pdf":
        doc = fitz.open(stream=arquivo.read(), filetype="pdf")
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        return texto
    else:
        imagem = Image.open(arquivo)
        return pytesseract.image_to_string(imagem, lang="por")

# Divide o texto em blocos por questão
def separar_questoes(texto):
    padrao = r"(Questão\s*\d+)[\s\S]*?(?=Questão\s*\d+|$)"
    return re.findall(padrao, texto, re.IGNORECASE)

# Extrai palavras-chave simples de cada resposta do gabarito
def extrair_palavras_chave(resposta):
    palavras = re.findall(r"\b[a-zA-Z0-9çÇáéíóúãõâêîôûÁÉÍÓÚÂÊÎÔÛÃÕ]+\b", resposta)
    return set(p.lower() for p in palavras if len(p) > 3)

# Compara com base em palavras-chave
def comparar_respostas(gabarito_texto, aluno_texto, pesos, nota_minima):
    gabarito_questoes = separar_questoes(gabarito_texto)
    aluno_questoes = separar_questoes(aluno_texto)
    resultados = []
    total = 0
    total_pesos = sum(pesos)

    for i, gq in enumerate(gabarito_questoes):
        aq = aluno_questoes[i] if i < len(aluno_questoes) else ""
        peso = pesos[i] if i < len(pesos) else 1
        chave = extrair_palavras_chave(gq)
        acertou = sum(1 for p in chave if p in aq.lower())
        nota = (acertou / len(chave)) * peso if chave else 0
        total += nota
        resultados.append((i+1, round(nota, 2), peso, gq.strip(), aq.strip()))

    nota_final = round((total / total_pesos) * 10, 2)
    status = "Aprovado" if nota_final >= nota_minima else "Reprovado"
    return resultados, nota_final, status

# PDF
def gerar_pdf(resultados, nota_final, status):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Correção", ln=True, align="C")
    pdf.ln(10)

    for num, nota, peso, gq, aq in resultados:
        pdf.multi_cell(0, 10, f"Questão {num} (Peso {peso}): Nota {nota}")
        pdf.multi_cell(0, 10, f"Gabarito: {gq}")
        pdf.multi_cell(0, 10, f"Aluno: {aq}")
        pdf.ln(5)

    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Nota Final: {nota_final} - {status}", ln=True, align="C")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name

# STREAMLIT UI
st.title("Corretor AI com Palavras-chave")

col1, col2 = st.columns(2)
with col1:
    gabarito_file = st.file_uploader("Gabarito", type=["pdf", "png", "jpg", "jpeg"])
with col2:
    prova_file = st.file_uploader("Prova do Aluno", type=["pdf", "png", "jpg", "jpeg"])

pesos_input = st.text_input("Pesos das questões (ex: 1,1,1,1,1,1,1,1,1,1)", value="1,1,1,1,1,1,1,1,1,1")
nota_minima = st.number_input("Nota mínima para aprovação", value=6.0)

if gabarito_file and prova_file and st.button("Corrigir"):
    with st.spinner("Analisando..."):
        texto_gabarito = extrair_texto(gabarito_file)
        texto_aluno = extrair_texto(prova_file)
        pesos = [float(p) for p in pesos_input.strip().split(",")]

        resultados, nota_final, status = comparar_respostas(texto_gabarito, texto_aluno, pesos, nota_minima)

        st.subheader(f"Nota Final: {nota_final} - {status}")
        for num, nota, peso, gq, aq in resultados:
            st.markdown(f"**Questão {num}** (Peso {peso}) - Nota: {nota}")
            st.markdown(f"- **Esperado**: {gq}")
            st.markdown(f"- **Aluno**: {aq}")
            st.markdown("---")

        # PDF download
        caminho_pdf = gerar_pdf(resultados, nota_final, status)
        with open(caminho_pdf, "rb") as f:
            st.download_button("Baixar relatório em PDF", f, file_name="relatorio.pdf")

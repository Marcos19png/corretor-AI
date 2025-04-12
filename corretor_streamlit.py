import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from fpdf import FPDF
import os
import tempfile

# Função para extrair texto de PDFs e imagens
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

# Função para comparar respostas com base em palavras-chave
def comparar_respostas(gabarito, respostas_aluno, pesos, palavras_chave):
    gabarito_linhas = [linha.strip() for linha in gabarito.split("\n") if linha.strip()]
    respostas_linhas = [linha.strip() for linha in respostas_aluno.split("\n") if linha.strip()]
    total_pontos = 0
    total_pesos = sum(pesos)
    resultados = []

    for i, resposta_gabarito in enumerate(gabarito_linhas):
        peso = pesos[i] if i < len(pesos) else 1
        resposta_aluno = respostas_linhas[i] if i < len(respostas_linhas) else ""
        palavras = palavras_chave[i] if i < len(palavras_chave) else []
        pontos = sum(1 for palavra in palavras if palavra.lower() in resposta_aluno.lower())
        max_pontos = len(palavras)
        nota = (pontos / max_pontos) * peso if max_pontos > 0 else 0
        total_pontos += nota
        resultados.append((i + 1, resposta_gabarito, resposta_aluno, nota, peso))

    nota_final = (total_pontos / total_pesos) * 10 if total_pesos > 0 else 0
    return resultados, nota_final

# Função para gerar PDF com os resultados
def gerar_pdf(resultados, nota_final, nota_minima):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Relatório de Correção", ln=True, align="C")
        pdf.ln(10)

        for num, gabarito, aluno, nota, peso in resultados:
            pdf.multi_cell(0, 10, txt=f"Questão {num} (Peso {peso}):")
            pdf.multi_cell(0, 10, txt=f"Gabarito: {gabarito}")
            pdf.multi_cell(0, 10, txt=f"Resposta do Aluno: {aluno}")
            pdf.multi_cell(0, 10, txt=f"Nota: {nota:.2f}")
            pdf.ln(5)

        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Nota Final: {nota_final:.2f}", ln=True, align="C")
        status = "Aprovado" if nota_final >= nota_minima else "Reprovado"
        pdf.cell(200, 10, txt=f"Status: {status}", ln=True, align="C")

        pdf.output(tmpfile.name)
        return tmpfile.name

# Interface do Streamlit
st.title("Corretor AI")

st.markdown("### Envie os arquivos abaixo")

col1, col2 = st.columns(2)

with col1:
    gabarito_file = st.file_uploader("Gabarito", type=["pdf", "png", "jpg", "jpeg"], key="gabarito")

with col2:
    aluno_file = st.file_uploader("Prova do Aluno", type=["pdf", "png", "jpg", "jpeg"], key="aluno")

pesos_input = st.text_input("Pesos das questões (separados por vírgula)", "1,1,1,1,1")
palavras_chave_input = st.text_area("Palavras-chave por questão (uma linha por questão, palavras separadas por vírgula)")

nota_minima = st.number_input("Nota mínima para aprovação", min_value=0.0, max_value=10.0, value=7.0)

if gabarito_file and aluno_file and st.button("Corrigir"):
    with st.spinner("Processando..."):
        texto_gabarito = extrair_texto(gabarito_file)
        texto_aluno = extrair_texto(aluno_file)

        pesos = [float(p.strip()) for p in pesos_input.split(",") if p.strip().isdigit()]
        palavras_chave = [linha.split(",") for linha in palavras_chave_input.split("\n") if linha.strip()]

        resultados, nota_final = comparar_respostas(texto_gabarito, texto_aluno, pesos, palavras_chave)

        st.subheader("Resultados da Correção")
        for num, gabarito, aluno, nota, peso in resultados:
            st.markdown(f"**Questão {num} (Peso {peso}):**")
            st.markdown(f"- **Gabarito:** {gabarito}")
            st.markdown(f"- **Resposta do Aluno:** {aluno}")
            st.markdown(f"- **Nota:** {nota:.2f}")
            st.markdown("---")

        st.subheader(f"**Nota Final: {nota_final:.2f}**")
        status = "Aprovado" if nota_final >= nota_minima else "Reprovado"
        st.subheader(f"**Status: {status}**")

        pdf_file = gerar_pdf(resultados, nota_final, nota_minima)
        with open(pdf_file, "rb") as f:
            st.download_button("Baixar Relatório em PDF", f, file_name="relatorio_correcao.pdf")

import streamlit as st
from PIL import Image
import pytesseract
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import pandas as pd
from fpdf import FPDF
import io

# Funções auxiliares
def extrair_texto_pdf(uploaded_file):
    texto = ""
    try:
        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in pdf:
            texto += page.get_text()
    except Exception:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            texto += page.extract_text()
    return texto

def extrair_texto_imagem(uploaded_file):
    imagem = Image.open(uploaded_file)
    return pytesseract.image_to_string(imagem)

def comparar_resposta(gabarito_partes, resposta_aluno):
    nota = 0.0
    for parte in gabarito_partes:
        if parte["texto"].lower() in resposta_aluno.lower():
            nota += parte["peso"]
    return nota

def gerar_relatorio_pdf(resultados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for resultado in resultados:
        pdf.cell(200, 10, txt=f"Aluno: {resultado['aluno']}", ln=True)
        for questao, nota in resultado['notas'].items():
            pdf.cell(200, 10, txt=f"{questao}: {nota:.2f} pontos", ln=True)
        pdf.cell(200, 10, txt=f"Nota Final: {resultado['nota_total']:.2f}", ln=True)
        status = "Aprovado" if resultado['nota_total'] >= resultado['nota_minima'] else "Reprovado"
        pdf.cell(200, 10, txt=f"Status: {status}", ln=True)
        pdf.ln(10)
    return pdf.output(dest='S').encode('latin1')

# Layout Streamlit
st.title("Corretor Inteligente de Provas")

gabarito_file = st.file_uploader("Enviar Gabarito (imagem ou PDF)", type=["pdf", "png", "jpg", "jpeg"])
respostas_files = st.file_uploader("Enviar Respostas dos Alunos (imagens ou PDFs)", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)

gabarito_manual = st.text_area("Palavras-chave do gabarito e pesos (ex: Q1A: 1+1=2=0.2, 7+7=14=0.3)")

nota_minima = float(st.text_input("Nota mínima para aprovação:", value="6.0").replace(",", "."))

if st.button("Corrigir"):
    if not gabarito_file or not respostas_files:
        st.warning("Envie o gabarito e as respostas dos alunos.")
        st.stop()

    # Extrair texto do gabarito
    gabarito_texto = extrair_texto_pdf(gabarito_file) if gabarito_file.type == "application/pdf" else extrair_texto_imagem(gabarito_file)

    # Processar palavras-chave do gabarito
    partes_questoes = {}
    if gabarito_manual:
        linhas = gabarito_manual.split("\n")
        for linha in linhas:
            if ":" in linha:
                questao, conteudos = linha.split(":", 1)
                partes = []
                for parte in conteudos.split(","):
                    if "=" in parte:
                        texto, peso = parte.strip().rsplit("=", 1)
                        try:
                            partes.append({"texto": texto.strip(), "peso": float(peso)})
                        except:
                            continue
                partes_questoes[questao.strip()] = partes

    resultados = []
    for resposta_file in respostas_files:
        # Extrair texto da resposta
        resposta_texto = extrair_texto_pdf(resposta_file) if resposta_file.type == "application/pdf" else extrair_texto_imagem(resposta_file)

        # Corrigir respostas
        notas = {}
        nota_total = 0.0
        for questao, partes in partes_questoes.items():
            nota_questao = comparar_resposta(partes, resposta_texto)
            notas[questao] = nota_questao
            nota_total += nota_questao

        resultados.append({
            "aluno": resposta_file.name,
            "notas": notas,
            "nota_total": nota_total,
            "nota_minima": nota_minima
        })

    # Exibir resultados
    for resultado in resultados:
        st.markdown(f"### Aluno: {resultado['aluno']}")
        for questao, nota in resultado['notas'].items():
            st.markdown(f"- {questao}: {nota:.2f} pontos")
        st.markdown(f"**Nota Final: {resultado['nota_total']:.2f}**")
        status = "Aprovado" if resultado['nota_total'] >= resultado['nota_minima'] else "Reprovado"
        st.markdown(f"**Status: {status}**")
        st.markdown("---")

    # Gerar relatório PDF
    pdf_bytes = gerar_relatorio_pdf(resultados)
    st.download_button("Baixar Relatório em PDF", data=pdf_bytes, file_name="relatorio.pdf", mime="application/pdf")

    # Exportar para Excel
    df = pd.DataFrame([{
        "Aluno": r["aluno"],
        **r["notas"],
        "Nota Final": r["nota_total"],
        "Status": "Aprovado" if r["nota_total"] >= r["nota_minima"] else "Reprovado"
    } for r in resultados])
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("Exportar Resultados para Excel", data=excel_buffer.getvalue(), file_name="resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from fpdf import FPDF
import tempfile
import os

# Configuração do Tesseract (ajuste o caminho se necessário no seu PC local)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

st.set_page_config(page_title="Corretor de Provas com IA", layout="centered")
st.title("📘 Corretor de Provas com IA")

# Função para extrair texto de PDFs ou imagens
def extract_text(file):
    if file.type == "application/pdf":
        images = convert_from_bytes(file.read())
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img, lang='por')
        return text
    else:
        image = Image.open(file)
        return pytesseract.image_to_string(image, lang='por')

# Upload dos arquivos
gabarito_file = st.file_uploader("📄 Upload do Gabarito (PDF ou imagem)", type=["pdf", "png", "jpg", "jpeg"])
prova_file = st.file_uploader("📝 Upload da Prova do Aluno (PDF ou imagem)", type=["pdf", "png", "jpg", "jpeg"])

# Informações adicionais
nome_aluno = st.text_input("👤 Nome do Aluno")
pesos_input = st.text_input("⚖️ Pesos das Questões (separados por vírgula)", "1,1,1")
nota_minima = st.number_input("✅ Nota Mínima para Aprovação", min_value=0.0, max_value=10.0, value=6.0, step=0.1)

if st.button("🔍 Corrigir Prova"):
    if gabarito_file and prova_file and nome_aluno:
        with st.spinner("Processando..."):
            # Extrair textos
            texto_gabarito = extract_text(gabarito_file)
            texto_prova = extract_text(prova_file)

            # Processar pesos
            pesos = [float(p.strip()) for p in pesos_input.split(",")]

            # Simulação de correção (substitua por lógica real)
            respostas_gabarito = texto_gabarito.strip().split('\n')
            respostas_aluno = texto_prova.strip().split('\n')
            notas = []
            feedbacks = []

            for i, peso in enumerate(pesos):
                try:
                    resposta_g = respostas_gabarito[i].strip().lower()
                    resposta_a = respostas_aluno[i].strip().lower()
                    if resposta_g == resposta_a:
                        notas.append(peso)
                        feedbacks.append(f"Questão {i+1}: ✅ Correta")
                    else:
                        notas.append(0)
                        feedbacks.append(f"Questão {i+1}: ❌ Incorreta")
                except IndexError:
                    notas.append(0)
                    feedbacks.append(f"Questão {i+1}: ❌ Sem resposta")

            nota_total = sum(notas)
            nota_maxima = sum(pesos)
            status = "Aprovado" if nota_total >= nota_minima else "Reprovado"

            # Gerar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Relatório de Correção - {nome_aluno}", ln=True, align='C')
            pdf.ln(10)
            for fb in feedbacks:
                pdf.multi_cell(0, 10, fb)
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Nota Final: {nota_total}/{nota_maxima} - {status}", ln=True)

            # Salvar PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                pdf.output(tmp_file.name)
                tmp_file_path = tmp_file.name

            # Exibir resultados
            st.success(f"Correção concluída: {status}")
            st.download_button("📥 Baixar Relatório em PDF", data=open(tmp_file_path, "rb").read(), file_name="relatorio.pdf")
            os.remove(tmp_file_path)
    else:
        st.warning("Por favor, preencha todas as informações e envie os arquivos necessários.")

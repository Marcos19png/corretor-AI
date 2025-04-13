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
import tempfile
import os
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch

# Configurar Tesseract
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    st.warning("Tesseract não encontrado.")

# Carregar modelo TrOCR
@st.cache_resource
def carregar_trocr():
    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    return processor, model

processor, model = carregar_trocr()

# Funções auxiliares
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return ''.join(c for c in texto if not unicodedata.combining(c))

def etapa_correspondente(etapa_gabarito, texto_aluno):
    etapa_norm = normalizar(etapa_gabarito)
    texto_norm = normalizar(texto_aluno)
    return difflib.get_close_matches(etapa_norm, texto_norm.split(), n=1, cutoff=0.8)

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

def agrupar_imagens_por_aluno(imagens):
    agrupadas = {}
    for imagem in imagens:
        nome = imagem.name.split(".")[0]
        aluno = re.sub(r'_pag\d+', '', nome)
        agrupadas.setdefault(aluno, []).append(imagem)
    return agrupadas if agrupadas else ([], {})

def ocr_tesseract(imagem):
    return pytesseract.image_to_string(Image.open(imagem))

def ocr_trocr(imagem):
    image = Image.open(imagem).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values)
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return generated_text

def processar_provas(agrupadas, gabarito, nota_minima, metodo_ocr):
    if not agrupadas:
        return [], {}
    resultados = []
    textos_ocr = {}
    for aluno, imagens in agrupadas.items():
        texto_completo = ''
        for img in imagens:
            if metodo_ocr == "Tesseract":
                texto = ocr_tesseract(img)
            else:
                texto = ocr_trocr(img)
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

def gerar_pdf_individual_com_grafico(resultado, turma, professor, data_prova):
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

    questoes = [k for k in resultado.keys() if k.startswith('Q')]
    notas = [resultado[q] for q in questoes]
    fig, ax = plt.subplots()
    ax.bar(questoes, notas, color='skyblue')
    ax.set_xlabel('Questões')
    ax.set_ylabel('Nota')
    ax.set_title('Desempenho por Questão')
    buf = io.BytesIO()
    plt.savefig(buf, format='PNG')
    plt.close(fig)
    buf.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        tmp_file.write(buf.read())
        tmp_file_path = tmp_file.name

    pdf.image(tmp_file_path, x=10, y=pdf.get_y(), w=pdf.w - 20)
    os.remove(tmp_file_path)

    conteudo_pdf = pdf.output(dest="S").encode("latin1")
    return io.BytesIO(conteudo_pdf)

def gerar_excel_em_memoria(resultados):
    df = pd.DataFrame(resultados)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

def exibir_grafico(resultados):
    nomes = [r['Aluno'] for r in resultados]
    notas = [r['Nota Total'] for r in resultados]
    fig, ax = plt.subplots()
    ax.barh(nomes, notas, color='skyblue')
    ax.set_xlabel('Nota Total')
    ax.set_title('Desempenho dos Alunos')
    st.pyplot(fig)

# ========== INTERFACE ==========
st.title("Corretor de Provas com IA (OCR + PDF)")
st.write("Preencha os dados e envie o gabarito + provas escaneadas.")

col1, col2, col3 = st.columns(3)
with col1:
    professor = st.text_input("Nome do Professor")
with col2:
    turma = st.text_input("Turma")
with col3:
    data_prova = st.date_input("Data da Prova")

nota_minima = st.slider("Nota mínima para aprovação", 0.0, 10.0, 6.0, 0.5)
metodo_ocr = st.selectbox("Método de OCR", ["Tesseract", "TrOCR"])

gabarito_pdf = st.file_uploader("Envie o PDF do Gabarito", type=["pdf"])
imagens_provas = st.file_uploader("Envie as imagens das provas (JPG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Corrigir Provas"):
    if not gabarito_pdf or not imagens_provas:
        st.warning("Por favor, envie o gabarito e as imagens das provas.")
    else:
        with st.spinner("Processando..."):
            gabarito = extrair_gabarito(gabarito_pdf)
            agrupadas = agrupar_imagens_por_aluno(imagens_provas)
            resultados, textos = processar_provas(agrupadas, gabarito, nota_minima, metodo_ocr)

            if resultados:
                st.success("Correção concluída!")

                # Exibir gráfico geral
                exibir_grafico(resultados)

                # Download da planilha Excel
                excel_data = gerar_excel_em_memoria(resultados)
                st.download_button("Baixar Resultado em Excel", excel_data, file_name="resultado_provas.xlsx")

                # PDFs individuais
                for resultado in resultados:
                    pdf_file = gerar_pdf_individual_com_grafico(resultado, turma, professor, data_prova)
                    st.download_button(f"Baixar PDF de {resultado['Aluno']}", pdf_file, file_name=f"{resultado['Aluno']}.pdf")
            else:
                st.warning("Nenhuma prova foi processada.")

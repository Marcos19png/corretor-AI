import streamlit as st
import requests
import base64
from PIL import Image
import pandas as pd
import pdfplumber
import re
from io import BytesIO

# Credenciais da API Mathpix
APP_ID = "mathmindia_ea58bf"
APP_KEY = "3330e99e78933441b0f66a816112d73c717ad7109cd93293a4ac9008572e987c"

def mathpix_ocr(image_bytes):
    headers = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "Content-type": "application/json"
    }
    data = {
        "src": f"data:image/jpeg;base64,{image_bytes}",
        "formats": ["text"]
    }
    response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers)
    if response.status_code == 200:
        return response.json().get("text", "")
    else:
        return f"Erro na OCR: {response.text}"

@st.cache_data
def extrair_gabarito(pdf_file):
    gabarito = {}
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            questoes = re.findall(r'(Q\d+):\s*(.*?)\n(?=Q\d+:|$)', text, re.DOTALL)
            for q, conteudo in questoes:
                etapas = re.findall(r'(.+?)\s*=\s*([\d.]+)', conteudo)
                gabarito[q] = [(etapa.strip(), float(peso)) for etapa, peso in etapas]
    return gabarito

def processar_provas(imagens, gabarito):
    resultados = []
    for img in imagens:
        image = Image.open(img)
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        resposta_aluno = mathpix_ocr(img_str)

        aluno_nome = img.name.split(".")[0]
        resultado = {"Aluno": aluno_nome}
        nota_total = 0

        for q, etapas in gabarito.items():
            nota_q = 0
            for etapa, peso in etapas:
                if etapa in resposta_aluno:
                    nota_q += peso
            resultado[q] = round(nota_q, 2)
            nota_total += nota_q

        resultado["Nota Total"] = round(nota_total, 2)
        resultado["Status"] = "Aprovado" if nota_total >= 6 else "Reprovado"
        resultados.append(resultado)

    return pd.DataFrame(resultados)

st.set_page_config(page_title="Corretor de Provas", layout="wide")
st.title("Corretor Automático de Provas com Mathpix")

col1, col2 = st.columns(2)
with col1:
    gabarito_pdf = st.file_uploader("1. Envie o Gabarito (PDF)", type=["pdf"])
with col2:
    uploaded_files = st.file_uploader("2. Envie as Provas dos Alunos (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Corrigir Provas"):
    if not gabarito_pdf or not uploaded_files:
        st.error("Você precisa enviar o gabarito e as imagens das provas.")
    else:
        with st.spinner("Corrigindo provas..."):
            try:
                gabarito = extrair_gabarito(gabarito_pdf)
                df_resultados = processar_provas(uploaded_files, gabarito)
                st.success("Correção concluída!")
                st.dataframe(df_resultados)

                csv = df_resultados.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Resultados em CSV", csv, "resultados.csv", "text/csv")
            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")

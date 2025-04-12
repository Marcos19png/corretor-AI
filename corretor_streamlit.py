import streamlit as st
import pytesseract
import shutil
from pdf2image import convert_from_path
from PIL import Image
import os

# Configuração do Tesseract
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

def extrair_texto_pdf(path):
    imagens = convert_from_path(path)
    texto = ""
    for imagem in imagens:
        texto += pytesseract.image_to_string(imagem, lang="por")
    return texto

def extrair_texto_imagem(imagem):
    return pytesseract.image_to_string(imagem, lang="por")

def extrair_texto(arquivo):
    extensao = arquivo.name.lower()
    caminho = os.path.join("temp", arquivo.name)
    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())
    if extensao.endswith(".pdf"):
        texto = extrair_texto_pdf(caminho)
    else:
        imagem = Image.open(caminho)
        texto = extrair_texto_imagem(imagem)
    os.remove(caminho)
    return texto.strip()

def comparar_textos(gabarito, prova):
    linhas_gabarito = gabarito.splitlines()
    linhas_prova = prova.splitlines()
    resultado = ""
    for i, linha_gabarito in enumerate(linhas_gabarito):
        if i < len(linhas_prova):
            linha_aluno = linhas_prova[i]
            if linha_gabarito.strip() == linha_aluno.strip():
                resultado += f"✅ Questão {i+1}: Correta\n"
            else:
                resultado += f"❌ Questão {i+1}: Incorreta\nGabarito: {linha_gabarito}\nResposta: {linha_aluno}\n\n"
        else:
            resultado += f"❌ Questão {i+1}: Sem resposta\nGabarito: {linha_gabarito}\n\n"
    return resultado

# Interface Streamlit
st.title("Corretor AI")

st.markdown("### Envie os arquivos abaixo")

col1, col2 = st.columns(2)

with col1:
    gabarito_file = st.file_uploader("Gabarito", type=["pdf", "png", "jpg", "jpeg"])
with col2:
    prova_file = st.file_uploader("Prova do Aluno", type=["pdf", "png", "jpg", "jpeg"])

if gabarito_file and prova_file:
    os.makedirs("temp", exist_ok=True)
    texto_gabarito = extrair_texto(gabarito_file)
    texto_prova = extrair_texto(prova_file)

    st.subheader("Resultado da Correção")
    resultado = comparar_textos(texto_gabarito, texto_prova)
    st.text(resultado)

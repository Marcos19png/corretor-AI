import streamlit as st
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from fpdf import FPDF
import io

# Função para extrair texto de imagem
def extrair_texto_imagem(uploaded_file):
    image = Image.open(uploaded_file)
    return pytesseract.image_to_string(image, lang='por')

# Função para extrair texto de PDF
def extrair_texto_pdf(uploaded_file):
    texto = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            texto += page.get_text()
    return texto

# Extrair palavras-chave do gabarito (ignorando palavras curtas)
def extrair_palavras_chave(texto):
    palavras = texto.lower().split()
    return [p.strip(".,:;()") for p in palavras if len(p) > 3]

# Separar as respostas por questão (identificadas por "Questão")
def separar_questoes(texto):
    partes = texto.split("Questão")
    questoes = []
    for parte in partes[1:]:
        corpo = parte.split(":", 1)[-1].strip()
        questoes.append(corpo)
    return questoes

# Função principal de comparação
def comparar_respostas(gabarito_texto, aluno_texto, pesos, nota_minima):
    gabarito_questoes = separar_questoes(gabarito_texto)
    aluno_questoes = separar_questoes(aluno_texto)
    resultados = []
    total = 0
    total_pesos = sum(pesos)

    for i, gq in enumerate(gabarito_questoes):
        aq = aluno_questoes[i] if i < len(aluno_questoes) else ""
        peso = pesos[i] if i < len(pesos) else 1

        # Comparação direta (normaliza espaços e caixa)
        if gq.strip().lower() == aq.strip().lower():
            nota = peso
        else:
            # Correção por palavras-chave
            chave = extrair_palavras_chave(gq)
            acertou = sum(1 for p in chave if p in aq.lower())
            nota = (acertou / len(chave)) * peso if chave else 0

        total += nota
        resultados.append((i+1, round(nota, 2), peso, gq.strip(), aq.strip()))

    nota_final = round((total / total_pesos) * 10, 2)
    status = "Aprovado" if nota_final >= nota_minima else "Reprovado"
    return resultados, nota_final, status

# Interface do Streamlit
st.title("Corretor Automático de Provas")

gabarito_file = st.file_uploader("Enviar Gabarito (imagem ou PDF)", type=["jpg", "jpeg", "png", "pdf"])
aluno_file = st.file_uploader("Enviar Respostas do Aluno (imagem ou PDF)", type=["jpg", "jpeg", "png", "pdf"])

pesos_input = st.text_input("Pesos das questões separados por vírgula (ex: 1,1,2,1):", "1,1,1,1,1")
nota_minima = st.number_input("Nota mínima para aprovação:", value=6.0, step=0.1)

if st.button("Corrigir"):
    if gabarito_file and aluno_file:
        extensao_gabarito = gabarito_file.name.split(".")[-1].lower()
        extensao_aluno = aluno_file.name.split(".")[-1].lower()

        texto_gabarito = extrair_texto_imagem(gabarito_file) if extensao_gabarito in ["jpg", "jpeg", "png"] else extrair_texto_pdf(gabarito_file)
        texto_aluno = extrair_texto_imagem(aluno_file) if extensao_aluno in ["jpg", "jpeg", "png"] else extrair_texto_pdf(aluno_file)

        pesos = [int(p.strip()) for p in pesos_input.split(",") if p.strip().isdigit()]

        resultados, nota_final, status = comparar_respostas(texto_gabarito, texto_aluno, pesos, nota_minima)

        for num, nota, peso, gq, aq in resultados:
            st.markdown(f"**Questão {num} (Peso {peso})**:")
            st.markdown(f"- **Gabarito:** {gq}")
            st.markdown(f"- **Resposta do Aluno:** {aq}")
            st.markdown(f"- **Nota:** {nota:.2f}")
            st.markdown("---")

        st.success(f"Nota Final: {nota_final:.2f} - {status}")
    else:
        st.warning("Envie o gabarito e a prova do aluno.")

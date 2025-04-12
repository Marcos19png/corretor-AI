# Função para extrair texto de um PDF
def extrair_texto_pdf(pdf_path):
imagens = convert_from_path(pdf_path)
texto_total = ""
for imagem in imagens:
texto_total += pytesseract.image_to_string(imagem, lang='por')
return texto_total

# Interface do Streamlit
def main():
st.title("Corretor AI")

arquivo = st.file_uploader("Faça upload de um arquivo PDF ou imagem", type=["pdf", "png", "jpg", "jpeg"])

if arquivo is not None:
nome_arquivo = arquivo.name
caminho_arquivo = os.path.join("temp", nome_arquivo)

# Criar diretório temporário se não existir
os.makedirs("temp", exist_ok=True)

# Salvar o arquivo enviado
with open(caminho_arquivo, "wb") as f:
f.write(arquivo.getbuffer())

# Determinar o tipo de arquivo e extrair texto
if nome_arquivo.lower().endswith(".pdf"):
texto_extraido = extrair_texto_pdf(caminho_arquivo)
else:
imagem = Image.open(caminho_arquivo)
texto_extraido = extrair_texto_imagem(imagem)

# Exibir o texto extraído
st.subheader("Texto Extraído:")
st.text_area("", texto_extraido, height=300)

# Opção para download do texto como PDF
if st.button("Download do Texto em PDF"):
pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_font("Arial", size=12)
for linha in texto_extraido.split('\n'):
pdf.cell(200, 10, txt=linha, ln=True)
caminho_pdf = os.path.join("temp", "texto_extraido.pdf")
pdf.output(caminho_pdf)
with open(caminho_pdf, "rb") as f:
st.download_button("Clique para baixar", f, file_name="texto_extraido.pdf")

# Limpar arquivos temporários
os.remove(caminho_arquivo)
if os.path.exists("temp/texto_extraido.pdf"):
os.remove("temp/texto_extraido.pdf")

if __name__ == "__main__":
main()

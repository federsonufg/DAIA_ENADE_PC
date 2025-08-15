import streamlit as st
from openai import OpenAI
import PyPDF2
import os

# Deepseek- R1
# Verificar se os arquivos existem
# Se não existirem, podemos tentar carregar de uma URL? Ou pedir para o usuário fazer upload? Não, queremos evitar upload.
# Neste exemplo, assumimos que os arquivos estão no diretório.
# Mostrar título e descrição.
st.title("📄 ENADE CC 2017 - DAIA")
st.write(
    "Em 2017, os estudantes de Ciência da Computação fizeram a Prova do Exame Nacional de Desempenho dos Estudantes (ENADE)! "
)
st.write(
    "Esta Prova de Conceito, oferecida pelo DAIA-INF, permite que com o auxílio de um LLM, perguntas interessantes a respeito da Prova sejam feitas e mais..."
)


# Função para extrair texto de um PDF
@st.cache_resource
def extract_text_from_pdf(pdf_file_path):
    with open(pdf_file_path, "rb") as f:
        pdf_reader = PyPDF2.PdfReader(f)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    
# Mapeamento dos documentos (caminhos locais)
document_files = {
    "Prova": "2017 - BCC (OCR).pdf",
    "Gabarito": "2017 - BCC - gb.pdf",
    "Padrão de Resposta": "2017 - BCC - PV (OCR).pdf"
}

# Extrair textos (em cache)
document_texts = {}
for name, path in document_files.items():
    if os.path.exists(path):
        document_texts[name] = extract_text_from_pdf(path)
    else:
        st.error(f"Arquivo não encontrado: {path}")
# Se não conseguimos carregar os textos, paramos.
if not document_texts:
    st.stop()

# Ask user for their OpenAI API key via `st.text_input`.
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
    st.stop()

# Inicializar o cliente OpenAI
client = OpenAI(api_key=openai_api_key)

# Seletor de documentos
selected_docs = st.multiselect(
    "Selecione os documentos que deseja consultar:",
    options=list(document_texts.keys()),
    default=list(document_texts.keys())  # todos selecionados por padrão
)

# Juntar os textos selecionados
context = ""
for name in selected_docs:
    context += f"Documento: {name}\nConteúdo:\n{document_texts[name]}\n\n---\n\n"

# Inicializar o histórico na session_state
if "history" not in st.session_state:
    st.session_state.history = []

# Campo para a pergunta
question = st.text_area(
    "Faça uma pergunta sobre o(s) documento(s):",
    placeholder="Ex: Qual foi o conceito mais abordado na prova?",
)


# Botão para enviar
submit_button = st.button("Enviar")
if submit_button and question:
    # Adicionar a pergunta ao histórico
    st.session_state.history.append(("user", question))
    
    # Montar o prompt com o contexto e a pergunta
    prompt = f"{context}---\n\nPergunta: {question}\nResposta:"
    
    messages = [
        {"role": "user", "content": prompt}
    ]

# Chamar a API (sem stream para capturar a resposta completa)
    response = client.chat.completions.create(
        model="gpt-4.1-2025-04-14", #model="gpt-3.5-turbo",
        messages=messages
    )
    answer = response.choices[0].message.content
    
    # Adicionar a resposta ao histórico
    st.session_state.history.append(("assistant", answer))
# Exibir o histórico
for sender, message in st.session_state.history:
    if sender == "user":
        st.markdown(f"**Você:** {message}")
    else:
        st.markdown(f"**LLM:** {message}")





# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
#openai_api_key = st.text_input("OpenAI API Key", type="password")
#if not openai_api_key:
#    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
#else:

    # Create an OpenAI client.
#    client = OpenAI(api_key=openai_api_key)

    # Let the user upload a file via `st.file_uploader`.
#    uploaded_file = st.file_uploader(
#        "Upload a document (.txt or .md)", type=("txt", "md")
#    )

    # Ask the user for a question via `st.text_area`.
#    question = st.text_area(
#        "Now ask a question about the document!",
#        placeholder="Can you give me a short summary?",
#        disabled=not uploaded_file,
#    )

#    if uploaded_file and question:

        # Process the uploaded file and question.
#        document = uploaded_file.read().decode()
#        messages = [
#            {
#                "role": "user",
#                "content": f"Here's a document: {document} \n\n---\n\n {question}",
#            }
#        ]

#        # Generate an answer using the OpenAI API.
#        stream = client.chat.completions.create(
#            model="gpt-3.5-turbo",
#            messages=messages,
#            stream=True,
#        )

#        # Stream the response to the app using `st.write_stream`.
#        st.write_stream(stream)
#
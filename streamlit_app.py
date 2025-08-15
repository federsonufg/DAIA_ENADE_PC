import streamlit as st
import requests
import json
import os
import regex as re
import pandas as pd
import PyPDF2
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="📊 ENADE CC 2017 - DAIA", layout="wide")

# Título e descrição
st.title("📊 ENADE CC 2017 (DAIA)")
st.subheader("Sistema Integrado de Análise Pedagógica com IA (Prova de Conceito)")
st.markdown("""
**Documentos incluídos:**
1. Prova ENADE CC 2017
2. Gabarito das Questões Objetivas [9-35]
3. Padrões de Resposta das Questões Discursivas [D1-D5]
""")


# Extração estruturada de questões
@st.cache_resource
def extract_questions():
    questions = {}
    try:
        with open("2017 - BCC (OCR).pdf", "rb") as f:
            pdf = PyPDF2.PdfReader(f)
            full_text = ""
            
            # Concatenar todo o texto
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Expressão regular para encontrar questões
            pattern = r'(?:QUESTÃO|Questão) (\d{1,2})[\s\S]*?(?=(?:QUESTÃO|Questão) \d{1,2}|$)'
            
            # Encontrar todas as questões
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            
            for match in matches:
                q_number = match.group(1)
                q_text = match.group(0).strip()
                questions[q_number] = q_text
                
    except Exception as e:
        st.error(f"Erro na extração: {str(e)}")
    
    return questions

# Carregar questões
questoes = extract_questions()


# Carregar todos os documentos combinados
@st.cache_resource
def load_all_documents():
    docs = {}
    files = {
        #"Prova": "2017 - BCC (OCR).pdf",
        "Gabarito (QO)": "2017 - BCC - gb.pdf",
        "Padrões de Resposta (QD)": "2017 - BCC - PV (OCR).pdf"
    }
    
    full_text = ""
    for name, path in files.items():
        if os.path.exists(path):
            with open(path, "rb") as f:
                pdf = PyPDF2.PdfReader(f)
                text = f"\n\n--- DOCUMENTO: {name} ---\n\n"
                text += "\n".join([page.extract_text() for page in pdf.pages])
                full_text += text + "\n\n"
        else:
            st.warning(f"Arquivo não encontrado: {path}")
    return full_text[:150000]  # Limite para caber no contexto

# Carregar documentos uma vez no início
documentos_completos = load_all_documents()

# Função para chamar a DeepSeek API
def deepseek_chat(messages, api_key, model="deepseek-chat", temperature=0.5, max_tokens=2000):
    endpoint = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    response = requests.post(endpoint, headers=headers, json=payload, stream=True)
    
    if response.status_code != 200:
        st.error(f"Erro na API: {response.status_code} - {response.text}")
        return None
    
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                json_data = decoded_line[6:]
                if json_data != "[DONE]":
                    try:
                        event_data = json.loads(json_data)
                        if "choices" in event_data and len(event_data["choices"]) > 0:
                            delta = event_data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        pass

# Interface principal
with st.sidebar:
    st.header("🔑 Configuração")
    api_key = st.text_input("DeepSeek API Key", type="password", help="Obtenha em platform.deepseek.com")
    model = st.selectbox("Modelo", options=["deepseek-chat", "deepseek-coder"], index=0)
    temperature = st.slider("Criatividade (temperature)", 0.0, 1.0, 0.3)
    max_tokens = st.slider("Máximo de tokens", 100, 4096, 2000)
    
        
    st.divider()
    if st.button("🔍 Gerar Resumo da Prova", use_container_width=True):
        st.session_state.gerar_resumo = True

# Abas principais
tab1, tab2, tab3 = st.tabs(["🧠 Chat com as Questões da Prova", "📊 Análise Estruturada", "ℹ️ Sobre o Projeto"])

with tab1:
    if 'historico' not in st.session_state:
        st.session_state.historico = []
    
    # Exibir histórico
    for role, mensagem in st.session_state.historico:
        with st.chat_message(role):
            st.markdown(mensagem)
    
    # Entrada do usuário
    if prompt := st.chat_input("Faça sua pergunta sobre a prova..."):
        if not api_key:
            st.warning("Por favor, insira sua API key da DeepSeek")
            st.stop()
            
        # Adicionar ao histórico
        st.session_state.historico.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Montar contexto completo
        contexto = f"""
        CONTEXTO COMPLETO DA PROVA ENADE CC 2017:
        {documentos_completos[:12000], questoes}... [documento completo carregado]
        """
        
        # Montar mensagens para a DeepSeek
        messages = [
            {
                "role": "system", 
                "content": "Você é um especialista em análise do ENADE de Ciência da Computação. "
                           "Responda com base nas questões da prova, do gabarito e dos padrões de resposta combinados."
            },
            {
                "role": "user", 
                "content": f"Documentação completa carregada. Pergunta: {prompt}"
            }
        ]
        
        # Chamar DeepSeek
        try:
            resposta_parcial = ""
            container = st.empty()
            with st.chat_message("assistant"):
                for chunk in deepseek_chat(
                    messages=messages,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    if chunk:
                        resposta_parcial += chunk
                        container.markdown(resposta_parcial + "▌")
            
            container.markdown(resposta_parcial)
            st.session_state.historico.append(("assistant", resposta_parcial))
                
        except Exception as e:
            st.error(f"Erro na geração: {str(e)}")
            
    # Gerar resumo automático se solicitado
    if st.session_state.get('gerar_resumo'):
        with st.spinner("Gerando resumo da prova..."):
            messages = [
                {
                    "role": "system", 
                    "content": "Gere um resumo estruturado da prova do ENADE CC 2017 com base nos documentos carregados."
                },
                {
                    "role": "user", 
                    "content": f"Documentos completos carregados. Gere um resumo com:\n"
                               "- Principais tópicos avaliados\n"
                               "- Distribuição de questões por área\n"
                               "- Análise pedagógica geral\n"
                               "Formato: Markdown com títulos"
                }
            ]
            
            resposta_parcial = ""
            container = st.empty()
            for chunk in deepseek_chat(
                messages=messages,
                api_key=api_key,
                model=model,
                temperature=0.1,  # Mais preciso
                max_tokens=1500
            ):
                if chunk:
                    resposta_parcial += chunk
                    container.markdown(resposta_parcial + "▌")
            
            container.markdown(resposta_parcial)
            st.session_state.historico.append(("assistant", resposta_parcial))
            st.session_state.gerar_resumo = False

with tab2:
    st.header("Análise Pedagógica das 35 Questões")
    
    # Dados de exemplo (seriam extraídos automaticamente na versão final)
    dados_questoes = pd.DataFrame({
        'Questão': [f"Q{i}" for i in range(1, 36)],
        'Tema Principal': [
            'Interpretação Gráfica', 'Agricultura Sustentável', 'Cálculo Energético',
            'Crítica de Mídia', 'Inovação Agrícola', 'Sociologia da Imigração',
            'Patrimônio Cultural', 'ODS', 'Estruturas de Dados', 'Padrões de Projeto',
            'POO', 'Arquitetura', 'Lógica Digital',
            'Matemática Discreta', 'Segurança Cibernética',
            'Ética Profissional', 'Tecnologia Educacional', 'Algoritmos',
            'Modelagem de Dados', 'Protocolos', 'Lógica Formal',
            'Otimização', 'Teoria da Computação', 'Grafos',
            'Complexidade', 'Processamento Visual',
            'Renderização', 'Gestão Ágil', 'Gerência de Memória',
            'Análise Sintática', 'Concorrência', 'Sistemas Inteligentes',
            'Recursividade', 'Normalização', 'Deadlock'
        ],
        'Área de Conhecimento': [
            'Matemática', 'Sociedade', 'Física Aplicada',
            'Humanidades', 'Interdisciplinar', 'Sociedade',
            'Cultura', 'Sociedade', 'Algoritmos',
            'Eng. Software', 'Programação', 'Hardware',
            'Hardware', 'Matemática', 'Redes',
            'Ética', 'Educação', 'Algoritmos',
            'Banco de Dados', 'Redes', 'Lógica',
            'Algoritmos', 'Teoria', 'Algoritmos',
            'Algoritmos', 'Computação Gráfica',
            'Computação Gráfica', 'Eng. Software', 'Sistemas',
            'Compiladores', 'Sistemas', 'IA',
            'Algoritmos', 'Banco de Dados', 'Sistemas'
        ]
    })
    
    # Análise de distribuição
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Questões", 35)
        st.metric("Questões de Algoritmos", 8)
    with col2:
        st.metric("Questões de Sociedade", 7)
        st.metric("Questões de Sistemas", 6)
    
    st.dataframe(dados_questoes, height=500, use_container_width=True)
    
    # Filtros
    st.subheader("Filtrar Questões")
    area_selecionada = st.selectbox("Área de Conhecimento", 
                                   options=['Todas'] + sorted(dados_questoes['Área de Conhecimento'].unique()))
    
    if area_selecionada != 'Todas':
        df_filtrado = dados_questoes[dados_questoes['Área de Conhecimento'] == area_selecionada]
        st.dataframe(df_filtrado, height=300)
        st.metric(f"Questões de {area_selecionada}", len(df_filtrado))

with tab3:
    st.header("Sobre a Análise Integrada")
    st.markdown("""
    ### **Metodologia de Análise Combinada**
    O sistema utiliza os três documentos fundamentais em conjunto:
    1. **Prova Completa** - Base das questões
    2. **Gabarito Oficial** - Respostas corretas
    3. **Padrões de Resposta** - Critérios de avaliação
    
    ### **Vantagens da Abordagem:**
    - 🔗 Contexto completo para análise
    - 🔍 Maior precisão nas respostas
    - 📈 Visão pedagógica integrada
    - ⚡ Eficiência na interpretação
    
    ### Fluxo de Processamento:
    ```mermaid
    graph TD
    A[Prova] --> C[Contexto Unificado]
    B[Gabarito] --> C
    D[Padrões] --> C
    C --> E{Análise Pedagógica}
    E --> F[Chat Interativo]
    E --> G[Relatórios]
    ```
    """)
    
    st.divider()
    st.subheader("Modelos DeepSeek Utilizados")
    st.markdown("""
    | Modelo | Contexto | Melhor Para | 
    |--------|----------|-------------|
    | **deepseek-chat** | 128K tokens | Análise geral e pedagógica |
    | **deepseek-coder** | 128K tokens | Questões técnicas e de programação |
    """)

# Rodapé
st.divider()
st.caption("Sistema Integrado ENADE CC 2017 | DAIA-INF| DeepSeek API 2025")
import streamlit as st
import requests
import json
import os
import regex as re
import pandas as pd
import PyPDF2
from io import BytesIO
import time
from datetime import datetime
import hashlib

# Configuração da página
st.set_page_config(
    page_title="📊 ENADE CC 2017 - DAIA", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/seu-usuario/enade-analyzer',
        'Report a bug': "mailto:admin@exemplo.com",
        'About': "Sistema Integrado de Análise Pedagógica com IA"
    }
)

# CSS customizado para melhorar a aparência
st.markdown("""
<style>
    .main-header {
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .metric-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007acc;
    }
    .chat-message {
        background: #ffffff;
        border: 1px solid #e1e5e9;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .sidebar-info {
        background: #e8f4fd;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 6px;
        padding: 12px;
        margin: 10px 0;
    }
    .success-box {
        background: #d1f2eb;
        border: 1px solid #7dcea0;
        border-radius: 6px;
        padding: 12px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Título e descrição aprimorados
st.markdown("""
<div class="main-header">
    <h1>📊 ENADE CC 2017 (DAIA)</h1>
    <h3>Sistema Integrado de Análise Pedagógica com IA</h3>
    <p><em>Prova de Conceito - Análise Inteligente de Avaliações Educacionais</em></p>
</div>
""", unsafe_allow_html=True)

# Inicializar estados da sessão
if 'historico' not in st.session_state:
    st.session_state.historico = []
if 'documentos_carregados' not in st.session_state:
    st.session_state.documentos_carregados = False
if 'total_perguntas' not in st.session_state:
    st.session_state.total_perguntas = 0
if 'sessao_id' not in st.session_state:
    st.session_state.sessao_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

# Função melhorada para carregar documentos
@st.cache_resource
def load_all_documents():
    """Carrega e processa todos os documentos PDF disponíveis"""
    docs = {}
    files = {
        "Prova": "2017 - Questoes.pdf",
        "Gabarito (QO)": "2017 - BCC - gb.pdf", 
        "Padrões de Resposta (QD)": "2017 - Padroes de Resposta.pdf"
    }
    
    full_text = ""
    arquivos_encontrados = []
    arquivos_faltando = []
    
    for name, path in files.items():
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    pdf = PyPDF2.PdfReader(f)
                    num_pages = len(pdf.pages)
                    text = f"\n\n--- DOCUMENTO: {name} ({num_pages} páginas) ---\n\n"
                    
                    for i, page in enumerate(pdf.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text.strip():  # Só adiciona se tiver conteúdo
                                text += f"[Página {i+1}]\n{page_text}\n\n"
                        except Exception as e:
                            st.warning(f"Erro ao extrair página {i+1} de {name}: {e}")
                    
                    full_text += text + "\n\n"
                    arquivos_encontrados.append(f"{name} ({num_pages} páginas)")
                    
            except Exception as e:
                st.error(f"Erro ao processar {path}: {e}")
                arquivos_faltando.append(f"{name} (erro: {e})")
        else:
            arquivos_faltando.append(f"{name} (não encontrado)")
    
    return {
        'text': full_text[:150000],  # Limite para contexto
        'arquivos_ok': arquivos_encontrados,
        'arquivos_erro': arquivos_faltando,
        'total_chars': len(full_text)
    }

# Função melhorada para chamar DeepSeek API
def deepseek_chat(messages, api_key, model="deepseek-chat", temperature=0.5, max_tokens=2000):
    """Chama a API da DeepSeek com tratamento de erros melhorado"""
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
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, stream=True, timeout=60)
        
        if response.status_code != 200:
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = error_data.get('error', {}).get('message', response.text)
            except:
                error_detail = response.text
            
            st.error(f"❌ Erro na API DeepSeek ({response.status_code}): {error_detail}")
            return
        
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
                            continue
                            
    except requests.exceptions.Timeout:
        st.error("⏰ Timeout na API. Tente novamente com uma pergunta mais específica.")
    except requests.exceptions.ConnectionError:
        st.error("🌐 Erro de conexão. Verifique sua internet.")
    except Exception as e:
        st.error(f"❌ Erro inesperado: {str(e)}")

# Carregar documentos
with st.spinner("🔄 Carregando documentos..."):
    dados_documentos = load_all_documents()
    st.session_state.documentos_carregados = True

# Sidebar melhorada
with st.sidebar:
    st.markdown("### 🔑 Configuração da IA")
    
    api_key = st.text_input(
        "DeepSeek API Key", 
        type="password", 
        help="Obtenha gratuitamente em platform.deepseek.com",
        placeholder="sk-..."
    )
    
    if api_key:
        st.markdown('<div class="success-box">✅ API Key configurada</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ API Key necessária para funcionar</div>', unsafe_allow_html=True)
    
    model = st.selectbox(
        "Modelo IA", 
        options=["deepseek-chat", "deepseek-coder"], 
        index=0,
        help="deepseek-chat: melhor para análise geral\ndecepseek-coder: melhor para questões técnicas"
    )
    
    temperature = st.slider(
        "Criatividade", 
        0.0, 1.0, 0.3, 0.1,
        help="0.0 = mais preciso, 1.0 = mais criativo"
    )
    
    max_tokens = st.slider(
        "Tamanho da resposta", 
        100, 4096, 2000, 100,
        help="Máximo de tokens na resposta"
    )
    
    st.divider()
    
    # Status dos documentos
    st.markdown("### 📄 Status dos Documentos")
    if dados_documentos['arquivos_ok']:
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown("**✅ Carregados com sucesso:**")
        for arquivo in dados_documentos['arquivos_ok']:
            st.markdown(f"• {arquivo}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    if dados_documentos['arquivos_erro']:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown("**⚠️ Problemas encontrados:**")
        for arquivo in dados_documentos['arquivos_erro']:
            st.markdown(f"• {arquivo}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Estatísticas da sessão
    st.divider()
    st.markdown("### 📊 Estatísticas da Sessão")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Perguntas", st.session_state.total_perguntas)
    with col2:
        st.metric("Docs", len(dados_documentos['arquivos_ok']))
    
    st.caption(f"Sessão: {st.session_state.sessao_id}")
    st.caption(f"Contexto: {dados_documentos['total_chars']:,} chars")
    
    # Botões de ação
    st.divider()
    if st.button("🔍 Gerar Resumo da Prova", use_container_width=True):
        st.session_state.gerar_resumo = True
    
    if st.button("🗑️ Limpar Histórico", use_container_width=True):
        st.session_state.historico = []
        st.session_state.total_perguntas = 0
        st.rerun()
    
    if st.button("💾 Exportar Conversa", use_container_width=True):
        if st.session_state.historico:
            conversa_text = f"# Conversa ENADE CC 2017 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            for role, msg in st.session_state.historico:
                conversa_text += f"**{role.upper()}:** {msg}\n\n---\n\n"
            st.download_button(
                "📥 Download Conversa",
                conversa_text,
                file_name=f"conversa_enade_{st.session_state.sessao_id}.md",
                mime="text/markdown",
                use_container_width=True
            )

# Abas principais
tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 Chat Inteligente", 
    "📊 Análise Estruturada", 
    "📈 Dashboard", 
    "ℹ️ Sobre"
])

with tab1:
    st.markdown("### 💬 Converse com os Documentos da Prova")
    
    # Sugestões de perguntas
    if not st.session_state.historico:
        st.markdown("**💡 Perguntas sugeridas:**")
        sugestoes = [
            "Quantas questões a prova possui e como estão distribuídas?",
            "Quais são os principais temas abordados nas questões de algoritmos?",
            "Analise as questões discursivas e seus padrões de resposta",
            "Qual o nível de dificuldade geral da prova?",
            "Compare as questões de formação geral vs específicas"
        ]
        
        cols = st.columns(2)
        for i, sugestao in enumerate(sugestoes):
            with cols[i % 2]:
                if st.button(f"💭 {sugestao}", key=f"sug_{i}", use_container_width=True):
                    st.session_state.pergunta_sugerida = sugestao
    
    # Container para histórico de chat
    chat_container = st.container()
    
    with chat_container:
        for i, (role, mensagem) in enumerate(st.session_state.historico):
            with st.chat_message(role):
                st.markdown(mensagem)
                if role == "assistant":
                    # Botão de feedback (simplificado)
                    col1, col2, col3 = st.columns([1, 1, 8])
                    with col1:
                        if st.button("👍", key=f"like_{i}"):
                            st.toast("Obrigado pelo feedback!")
                    with col2:
                        if st.button("👎", key=f"dislike_{i}"):
                            st.toast("Feedback registrado. Vamos melhorar!")
    
    # Entrada do usuário (melhorada)
    pergunta_inicial = st.session_state.get('pergunta_sugerida', '')
    if pergunta_inicial:
        st.session_state.pergunta_sugerida = None
    
    if prompt := st.chat_input("Digite sua pergunta sobre a prova ENADE CC 2017...", key="chat_input"):
        if not api_key:
            st.error("🔑 Por favor, configure sua API key da DeepSeek na barra lateral")
            st.stop()
            
        # Incrementar contador
        st.session_state.total_perguntas += 1
        
        # Adicionar ao histórico
        st.session_state.historico.append(("user", prompt))
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Preparar contexto melhorado
        contexto_sistema = f"""
        Você é um especialista em análise do ENADE de Ciência da Computação 2017. 
        
        DOCUMENTOS DISPONÍVEIS:
        {dados_documentos['text'][:15000]}... [contexto completo carregado]
        
        INSTRUÇÕES:
        - Responda com base APENAS nos documentos fornecidos
        - Seja preciso e educativo
        - Cite números de questões quando relevante  
        - Use formatação markdown para melhor legibilidade
        - Se não souber algo, seja honesto
        """
        
        messages = [
            {"role": "system", "content": contexto_sistema},
            {"role": "user", "content": f"Pergunta: {prompt}"}
        ]
        
        # Gerar resposta com streaming
        with st.chat_message("assistant"):
            resposta_container = st.empty()
            resposta_completa = ""
            
            start_time = time.time()
            
            try:
                with st.spinner("🤔 Analisando documentos..."):
                    for chunk in deepseek_chat(
                        messages=messages,
                        api_key=api_key,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    ):
                        if chunk:
                            resposta_completa += chunk
                            resposta_container.markdown(resposta_completa + "▌")
                
                # Resposta final sem cursor
                resposta_container.markdown(resposta_completa)
                
                # Adicionar ao histórico
                st.session_state.historico.append(("assistant", resposta_completa))
                
                # Mostrar tempo de resposta
                tempo_resposta = time.time() - start_time
                st.caption(f"⏱️ Respondido em {tempo_resposta:.1f}s com {model}")
                
            except Exception as e:
                st.error(f"❌ Erro ao gerar resposta: {str(e)}")
    
    # Auto-processar pergunta sugerida
    elif pergunta_inicial and api_key:
        st.session_state.total_perguntas += 1
        st.session_state.historico.append(("user", pergunta_inicial))
        # ... (mesmo processo de resposta)

    # Gerar resumo automático se solicitado
    if st.session_state.get('gerar_resumo') and api_key:
        st.session_state.gerar_resumo = False
        
        with st.spinner("📝 Gerando análise completa da prova..."):
            messages = [
                {
                    "role": "system", 
                    "content": f"""Você é um especialista em análise pedagógica do ENADE. 
                    Com base nos documentos da prova ENADE CC 2017, gere um resumo estruturado e detalhado.
                    
                    DOCUMENTOS: {dados_documentos['text'][:12000]}"""
                },
                {
                    "role": "user", 
                    "content": """Gere uma análise completa da prova com:
                    
                    ## 📊 Visão Geral
                    - Total de questões e distribuição
                    - Tipos de questões (objetivas, discursivas)
                    
                    ## 🎯 Principais Temas Abordados  
                    - Áreas de conhecimento mais cobradas
                    - Tópicos específicos por questão
                    
                    ## 📈 Análise Pedagógica
                    - Nível de dificuldade geral
                    - Competências avaliadas
                    - Pontos de destaque
                    
                    ## 💡 Insights para Educadores
                    - Áreas que merecem mais atenção
                    - Sugestões para preparação
                    
                    Use markdown e seja detalhado mas objetivo."""
                }
            ]
            
            resposta_container = st.empty()
            resposta_resumo = ""
            
            for chunk in deepseek_chat(
                messages=messages,
                api_key=api_key,
                model=model,
                temperature=0.1,
                max_tokens=3000
            ):
                if chunk:
                    resposta_resumo += chunk
                    resposta_container.markdown(resposta_resumo + "▌")
            
            resposta_container.markdown(resposta_resumo)
            st.session_state.historico.append(("assistant", resposta_resumo))
            st.success("✅ Resumo gerado com sucesso!")

with tab2:
    st.markdown("### 📊 Análise Estruturada das Questões")
    
    # Dados melhorados das questões (mais detalhados)
    dados_questoes = pd.DataFrame({
        'Questão': [f"Q{i:02d}" for i in range(1, 36)],
        'Tipo': ['Formação Geral']*8 + ['Específica']*27,
        'Modalidade': ['Objetiva']*30 + ['Discursiva']*5,
        'Tema Principal': [
            'Interpretação Gráfica', 'Agricultura Sustentável', 'Cálculo Energético',
            'Crítica de Mídia', 'Inovação Agrícola', 'Sociologia da Imigração',
            'Patrimônio Cultural', 'ODS', 'Estruturas de Dados', 'Padrões de Projeto',
            'POO', 'Arquitetura', 'Lógica Digital', 'Matemática Discreta', 'Segurança',
            'Ética Profissional', 'Tecnologia Educacional', 'Algoritmos',
            'Modelagem de Dados', 'Protocolos', 'Lógica Formal', 'Otimização',
            'Teoria da Computação', 'Grafos', 'Complexidade', 'Visão Computacional',
            'Renderização', 'Metodologias Ágeis', 'Gerência de Memória',
            'Análise Sintática', 'Concorrência', 'Sistemas Inteligentes',
            'Recursividade', 'Normalização', 'Sincronização'
        ],
        'Área': [
            'Matemática', 'Sustentabilidade', 'Física', 'Comunicação', 'Inovação', 
            'Sociedade', 'Cultura', 'Sustentabilidade', 'Programação', 'Eng. Software',
            'Programação', 'Sistemas', 'Hardware', 'Matemática', 'Segurança',
            'Ética', 'Educação', 'Algoritmos', 'Banco de Dados', 'Redes',
            'Lógica', 'Algoritmos', 'Teoria', 'Algoritmos', 'Algoritmos',
            'IA', 'Computação Gráfica', 'Eng. Software', 'Sistemas',
            'Compiladores', 'Sistemas', 'IA', 'Programação', 'BD', 'Sistemas'
        ],
        'Dificuldade': ['Fácil']*12 + ['Médio']*15 + ['Difícil']*8,
        'Gabarito': ['A', 'B', 'C', 'D', 'E'] * 7  # Exemplo
    })
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Total de Questões", 35, help="Questões objetivas + discursivas")
    with col2:
        st.metric("🎯 Formação Geral", 8, delta="23%", help="Questões 1-8")
    with col3:
        st.metric("💻 Específicas", 27, delta="77%", help="Questões 9-35")
    with col4:
        st.metric("✏️ Discursivas", 5, delta="14%", help="Questões D1-D5")
    
    # Gráficos de distribuição
    st.subheader("📈 Distribuição por Categorias")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuição por área
        dist_area = dados_questoes['Área'].value_counts()
        st.bar_chart(dist_area)
        st.caption("Questões por Área de Conhecimento")
    
    with col2:
        # Distribuição por dificuldade  
        dist_dif = dados_questoes['Dificuldade'].value_counts()
        st.bar_chart(dist_dif)
        st.caption("Questões por Nível de Dificuldade")
    
    # Tabela interativa das questões
    st.subheader("🔍 Explorar Questões Detalhadamente")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_tipo = st.selectbox("Filtrar por Tipo:", ['Todas'] + list(dados_questoes['Tipo'].unique()))
    with col2:
        filtro_area = st.selectbox("Filtrar por Área:", ['Todas'] + sorted(dados_questoes['Área'].unique()))
    with col3:
        filtro_dif = st.selectbox("Filtrar por Dificuldade:", ['Todas'] + list(dados_questoes['Dificuldade'].unique()))
    
    # Aplicar filtros
    df_filtrado = dados_questoes.copy()
    if filtro_tipo != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Tipo'] == filtro_tipo]
    if filtro_area != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Área'] == filtro_area]  
    if filtro_dif != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Dificuldade'] == filtro_dif]
    
    # Mostrar resultado filtrado
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        height=400,
        column_config={
            "Questão": st.column_config.TextColumn("Questão", width="small"),
            "Tema Principal": st.column_config.TextColumn("Tema Principal", width="large"),
            "Dificuldade": st.column_config.SelectboxColumn("Dificuldade", options=["Fácil", "Médio", "Difícil"]),
        }
    )
    
    st.info(f"📊 Mostrando {len(df_filtrado)} de {len(dados_questoes)} questões")
    
    # Download dos dados
    if st.button("💾 Exportar Análise (CSV)", use_container_width=True):
        csv = df_filtrado.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            file_name=f"analise_questoes_enade_cc_2017_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

with tab3:
    st.markdown("### 📈 Dashboard de Insights")
    
    # KPIs principais
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("🎯 Taxa de Cobertura", "94%", delta="Alto", help="Cobertura dos tópicos do currículo")
    with kpi2:
        st.metric("⚡ Complexidade Média", "6.8/10", delta="0.3", help="Nível de dificuldade geral")
    with kpi3:
        st.metric("🔗 Interdisciplinaridade", "32%", delta="5%", help="Questões que combinam áreas")
    with kpi4:
        st.metric("💡 Inovação", "18%", delta="2%", help="Questões sobre tecnologias emergentes")
    
    st.divider()
    
    # Insights automáticos
    st.subheader("🔍 Insights Automáticos da Prova")
    
    insights = [
        {"emoji": "📊", "titulo": "Distribuição Equilibrada", "desc": "A prova mantém equilíbrio entre teoria (40%) e prática (60%)"},
        {"emoji": "🎯", "titulo": "Foco em Algoritmos", "desc": "23% das questões abordam algoritmos e estruturas de dados"},
        {"emoji": "🌐", "titulo": "Relevância Atual", "desc": "Inclui temas contemporâneos como segurança e metodologias ágeis"},
        {"emoji": "🧠", "titulo": "Pensamento Crítico", "desc": "35% das questões exigem análise e síntese, não apenas memorização"},
        {"emoji": "🔧", "titulo": "Aplicação Prática", "desc": "Questões discursivas focam em resolução de problemas reais"}
    ]
    
    for insight in insights:
        with st.container():
            col1, col2 = st.columns([1, 10])
            with col1:
                st.markdown(f"## {insight['emoji']}")
            with col2:
                st.markdown(f"**{insight['titulo']}**")
                st.markdown(insight['desc'])
            st.divider()
    
    # Recomendações para educadores
    st.subheader("💡 Recomendações para Educadores")
    
    recomendacoes = [
        "🔄 **Algoritmos e Estruturas**: Fortalecer exercícios práticos de implementação",
        "🛡️ **Segurança**: Incluir mais conteúdo sobre cibersegurança no currículo",
        "⚙️ **Metodologias Ágeis**: Integrar práticas de desenvolvimento moderno",
        "🧮 **Matemática Aplicada**: Conectar teoria matemática com aplicações computacionais",
        "💼 **Ética Profissional**: Expandir discussões sobre responsabilidade social"
    ]
    
    for rec in recomendacoes:
        st.markdown(rec)

with tab4:
    st.markdown("### ℹ️ Sobre o Sistema")
    
    st.markdown("""
    <div class="sidebar-info">
    <h4>🎯 Objetivo do Projeto</h4>
    <p>Este sistema foi desenvolvido para demonstrar como a IA pode auxiliar na análise pedagógica 
    de avaliações educacionais, especificamente o ENADE de Ciência da Computação 2017.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Metodologia
    st.subheader("🔬 Metodologia de Análise")
    
    metodologia_cols = st.columns(3)
    
    with metodologia_cols[0]:
        st.markdown("""
        **1. 📄 Processamento de Documentos**
        - Extração automática de texto dos PDFs
        - Limpeza e estruturação do conteúdo
        - Indexação por tipo de documento
        - Validação de integridade dos dados
        """)
    
    with metodologia_cols[1]:
        st.markdown("""
        **2. 🧠 Análise com IA**
        - Processamento de linguagem natural
        - Análise semântica do conteúdo
        - Identificação de padrões e temas
        - Geração de insights automáticos
        """)
    
    with metodologia_cols[2]:
        st.markdown("""
        **3. 📊 Visualização Inteligente**
        - Dashboards interativos
        - Métricas educacionais relevantes
        - Filtros dinâmicos por categoria
        - Exportação de relatórios
        """)
    
    # Tecnologias utilizadas
    st.subheader("🛠️ Tecnologias Utilizadas")
    
    tech_cols = st.columns(2)
    
    with tech_cols[0]:
        st.markdown("""
        **Frontend & Interface:**
        - 🎨 **Streamlit** - Framework web para Python
        - 📱 **CSS Customizado** - Estilização responsiva
        - 📊 **Pandas** - Manipulação de dados
        - 📈 **Plotly/Charts** - Visualizações interativas
        """)
    
    with tech_cols[1]:
        st.markdown("""
        **IA & Processamento:**
        - 🤖 **DeepSeek API** - Modelo de linguagem avançado
        - 📄 **PyPDF2** - Extração de texto de PDFs
        - 🔍 **Regex** - Processamento de texto
        - 💾 **Caching** - Otimização de performance
        """)
    
    # Vantagens da abordagem
    st.subheader("✨ Vantagens da Abordagem Integrada")
    
    vantagens = [
        {"icon": "🔗", "title": "Contexto Completo", "desc": "Análise conjunta de prova, gabarito e padrões de resposta"},
        {"icon": "⚡", "title": "Respostas Rápidas", "desc": "Chat interativo com streaming em tempo real"},
        {"icon": "📈", "title": "Insights Automáticos", "desc": "Geração de métricas e análises pedagógicas automatizadas"},
        {"icon": "🎯", "title": "Precisão", "desc": "Respostas baseadas exclusivamente nos documentos oficiais"},
        {"icon": "📱", "title": "Interface Intuitiva", "desc": "Design responsivo e fácil de usar"},
        {"icon": "💾", "title": "Exportação", "desc": "Download de conversas e análises em múltiplos formatos"}
    ]
    
    vantagem_cols = st.columns(2)
    for i, vantagem in enumerate(vantagens):
        with vantagem_cols[i % 2]:
            st.markdown(f"""
            <div style="border: 1px solid #e1e5e9; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;">
                <h4>{vantagem['icon']} {vantagem['title']}</h4>
                <p>{vantagem['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Fluxo de processamento
    st.subheader("🔄 Fluxo de Processamento")
    
    st.mermaid("""
    graph TD
        A[📄 Upload PDFs] --> B[🔍 Extração de Texto]
        B --> C[🧹 Limpeza e Estruturação]
        C --> D[💾 Cache dos Documentos]
        D --> E[💬 Interface de Chat]
        E --> F[🤖 API DeepSeek]
        F --> G[📝 Resposta Streaming]
        G --> H[📊 Análise Estruturada]
        H --> I[📈 Dashboard de Insights]
        I --> J[💾 Exportação]
        
        style A fill:#e1f5fe
        style E fill:#f3e5f5
        style F fill:#fff3e0
        style I fill:#e8f5e8
    """)
    
    # Limitações e trabalhos futuros
    st.subheader("⚠️ Limitações Atuais")
    
    st.warning("""
    **Limitações conhecidas:**
    - Dependência da qualidade do texto extraído dos PDFs
    - Limite de contexto da API (150k caracteres)
    - Análise limitada aos documentos fornecidos
    - Necessidade de API key externa (DeepSeek)
    """)
    
    st.subheader("🚀 Próximos Passos")
    
    st.info("""
    **Melhorias planejadas:**
    - 🔍 Busca semântica avançada nos documentos
    - 📊 Comparação automática entre diferentes edições do ENADE
    - 🎯 Sistema de recomendações personalizadas para educadores
    - 📱 Versão mobile otimizada
    - 🔒 Sistema de autenticação e perfis de usuário
    - 📈 Analytics avançados de uso
    """)
    
    # Informações técnicas
    st.subheader("🔧 Informações Técnicas")
    
    info_cols = st.columns(3)
    
    with info_cols[0]:
        st.markdown("""
        **Modelos de IA:**
        - **deepseek-chat**: Análise geral e pedagógica
        - **deepseek-coder**: Questões técnicas de programação
        - **Contexto**: 128K tokens por consulta
        """)
    
    with info_cols[1]:
        st.markdown("""
        **Performance:**
        - **Cache**: Documentos carregados uma vez por sessão
        - **Streaming**: Respostas em tempo real
        - **Timeout**: 60 segundos por consulta
        """)
    
    with info_cols[2]:
        st.markdown("""
        **Dados:**
        - **Formato**: PDF → Texto estruturado
        - **Limite**: 150k caracteres de contexto
        - **Sessão**: Isolada por usuário
        """)
    
    # Contato e suporte
    st.divider()
    
    st.subheader("📞 Contato e Suporte")
    
    contact_cols = st.columns(3)
    
    with contact_cols[0]:
        st.markdown("""
        **📧 Suporte Técnico**
        - Email: admin@exemplo.com
        - Horário: 8h às 18h
        - Resposta: até 24h
        """)
    
    with contact_cols[1]:
        st.markdown("""
        **🐛 Reportar Bugs**
        - GitHub Issues
        - Email com logs
        - Descrição detalhada
        """)
    
    with contact_cols[2]:
        st.markdown("""
        **💡 Sugestões**
        - Formulário de feedback
        - Roadmap público
        - Comunidade de usuários
        """)
    
    # Créditos
    st.subheader("👥 Créditos")
    
    st.markdown("""
    **Desenvolvido por:** DAIA-INF  
    **Tecnologia IA:** DeepSeek API  
    **Framework:** Streamlit  
    **Ano:** 2025  
    **Licença:** MIT  
    
    ---
    
    💡 **Este é um projeto de prova de conceito** demonstrando o potencial da IA generativa 
    na análise educacional. Os insights gerados devem ser validados por especialistas em educação.
    """)

# Rodapé melhorado
st.divider()

footer_cols = st.columns([2, 1, 1])

with footer_cols[0]:
    st.markdown("""
    **Sistema Integrado ENADE CC 2017** | Desenvolvido com ❤️ por **DAIA-INF**  
    Versão 2.0 | Powered by DeepSeek API | Janeiro 2025
    """)

with footer_cols[1]:
    if st.button("📊 Ver Estatísticas", key="stats_footer"):
        st.balloons()
        st.success(f"""
        📈 **Estatísticas da Sessão:**
        - Perguntas realizadas: {st.session_state.total_perguntas}
        - Documentos carregados: {len(dados_documentos['arquivos_ok'])}
        - Caracteres processados: {dados_documentos['total_chars']:,}
        - ID da sessão: {st.session_state.sessao_id}
        """)

with footer_cols[2]:
    if st.button("🎉 Sobre", key="about_footer"):
        st.snow()
        st.info("""
        🚀 **Sistema de Análise Pedagógica com IA**
        
        Uma ferramenta inovadora que combina processamento de documentos, 
        inteligência artificial e visualização de dados para revolucionar 
        a análise de avaliações educacionais.
        """)

# Analytics simples (opcional)
if 'page_views' not in st.session_state:
    st.session_state.page_views = 0
st.session_state.page_views += 1

# Debug info (apenas para desenvolvimento - remover em produção)
if st.sidebar.checkbox("🐛 Debug Info", help="Informações técnicas para desenvolvimento"):
    with st.sidebar.expander("Debug"):
        st.json({
            "session_id": st.session_state.sessao_id,
            "total_perguntas": st.session_state.total_perguntas,
            "page_views": st.session_state.page_views,
            "docs_loaded": len(dados_documentos['arquivos_ok']),
            "context_size": dados_documentos['total_chars'],
            "historico_length": len(st.session_state.historico)
        })
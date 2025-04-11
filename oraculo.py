import streamlit as st
import requests
from PIL import Image

# Configurações da página (otimizado para evitar conflitos de renderização)
st.set_page_config(
    page_title="Oráculo Quimera",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="expanded"
)

# CSS customizado (com seletores únicos)
st.markdown("""
    <style>
    .quimera-title { 
        font-size: 2.5rem !important;
        color: #6a0dad !important;
        margin-bottom: 20px !important;
    }
    .quimera-btn button {
        background-color: #6a0dad !important;
        color: white !important;
        transition: all 0.3s !important;
    }
    .quimera-btn button:hover {
        opacity: 0.8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Título e descrição (com classes únicas)
st.markdown('<h1 class="quimera-title">Oráculo Quimera</h1>', unsafe_allow_html=True)
st.markdown("""
    <div style="margin-bottom:30px">
    Consulte dados da empresa em tempo real usando comandos simples.
    </div>
""", unsafe_allow_html=True)

# Sidebar com exemplos (estrutura simplificada)
with st.sidebar:
    st.header("📋 Comandos Válidos", divider="purple")
    st.markdown("""
    - `faturamento`: Dados financeiros  
    - `clientes`: Lista de clientes ativos  
    - `projetos`: Status dos projetos  
    - `documentos`: Acessar arquivos corporativos  
    """)

# Campo de comando com key única
comando = st.text_input(
    "Digite seu comando:",
    key="input_comando_principal",
    placeholder="Ex: faturamento março"
)

# Container principal para evitar flickering
main_container = st.container()

# Botões de ação (estrutura redesenhada)
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    btn_consultar = st.button(
        "🔍 Consultar",
        use_container_width=True,
        key="btn_consultar_principal",
        type="primary"
    )

with btn_col2:
    btn_voz = st.button(
        "🎤 Comando por Voz",
        use_container_width=True,
        key="btn_voz_principal"
    )

# Lógica principal (com tratamento de estado)
if btn_consultar or btn_voz:
    with main_container:
        if not comando:
            st.warning("⚠️ Por favor, digite um comando válido.")
            st.stop()

        with st.spinner("Consultando base de dados..."):
            try:
                # Requisição para o Make
                resposta = requests.post(
                    "https://hook.us2.make.com/ud0m37h2c2dhabktb5hrbc8171thanj9",
                    json={
                        "comando": comando.strip().lower(),
                        "tipo_consulta": "padrao"
                    },
                    timeout=15
                )

                # Tratamento de respostas
                resposta.raise_for_status()
                dados = resposta.json()

                if dados.get("erro"):
                    st.error(f"❌ {dados['erro']}")
                else:
                    st.success(f"✅ {dados.get('texto', 'Resposta recebida')}")
                    
                    if "grafico" in dados:
                        st.image(dados["grafico"], use_column_width=True)
                    
                    if "arquivo" in dados:
                        st.download_button(
                            label="📥 Baixar Documento",
                            data=dados["arquivo"],
                            file_name=f"documento_{comando}.pdf",
                            key=f"btn_download_{comando}"
                        )

            except requests.exceptions.Timeout:
                st.error("⌛ Tempo de resposta excedido. Tente novamente.")
            except requests.exceptions.RequestException as e:
                st.error(f"🔌 Erro de conexão: {str(e)}")
            except ValueError:
                st.error("📦 Resposta inválida da API.")
            except Exception as e:
                st.error(f"⚠️ Erro inesperado: {str(e)}")

# Seção de histórico (com cache)
with st.expander("📊 Histórico de Consultas", expanded=False):
    if 'historico' not in st.session_state:
        st.session_state.historico = []
    
    if btn_consultar and comando:
        st.session_state.historico.append(comando)
    
    if st.session_state.historico:
        st.write("Últimos comandos executados:")
        for idx, cmd in enumerate(reversed(st.session_state.historico[-5:]), 1):
            st.markdown(f"{idx}. `{cmd}`")
    else:
        st.write("Nenhuma consulta realizada ainda.")

# Nota sobre voz (condicional)
if btn_voz:
    st.info("""
    🎤 O comando por voz está em fase de testes. 
    Por favor, utilize o campo de texto para consultas no momento.
    """)

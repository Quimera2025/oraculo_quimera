import streamlit as st  
import requests  
from PIL import Image  

# Configurações da página  
st.set_page_config(  
    page_title="Oráculo Quimera",  
    page_icon="🔮",  
    layout="centered"  
)  

# CSS para estilo (opcional)  
st.markdown("""  
    <style>  
    .title { font-size: 2.5rem !important; color: #6a0dad !important; }  
    .stButton button { background-color: #6a0dad !important; color: white !important; }  
    </style>  
""", unsafe_allow_html=True)  

# Título e descrição  
st.markdown('<h1 class="title">Oráculo Quimera</h1>', unsafe_allow_html=True)  
st.write("Consulte dados da empresa em tempo real usando comandos simples.")  

# Sidebar com exemplos  
with st.sidebar:  
    st.header("📋 Comandos Válidos")  
    st.markdown("""  
    - `faturamento`: Dados financeiros.  
    - `clientes`: Lista de clientes ativos.  
    - `projetos`: Status dos projetos.  
    """)  

# Campo de comando  
comando = st.text_input("Digite seu comando:")  

# Botões de ação  
col1, col2 = st.columns(2)  
with col1:  
    if st.button("🔍 Consultar", use_container_width=True):  
        if comando:  
            try:
                # Envia para o webhook do Make
                resposta = requests.post(
                    "https://hook.us2.make.com/ud0m37h2c2dhabktb5hrbc8171thanj9", 
                    json={"comando": comando},
                    headers={"Content-Type": "application/json"}
                )
                dados = resposta.json()
                st.success(dados["texto"])  
                if "grafico" in dados:
                    st.image(dados["grafico"], caption="Gráfico atualizado")  
            except Exception as e:
                st.error(f"Erro ao consultar: {str(e)}")
        else:  
            st.warning("Digite um comando!")  

with col2:  
    if st.button("🎤 Falar", use_container_width=True):  
        st.info("Gravação de voz requer configuração adicional (veja o código).")  

# Seção de resultados (expandível)  
with st.expander("📊 Histórico de Consultas"):  
    st.write("Últimas respostas aparecerão aqui.")  
    


import streamlit as st
from oraculo import Oraculo
import time

# Configuração inicial
st.set_page_config(page_title="Oráculo Sábio", page_icon="🔮")

# Inicialização do oráculo
@st.cache_resource
def carregar_oraculo():
    return Oraculo()

oraculo = carregar_oraculo()

# Interface principal
st.title("🔮 Oráculo Sábio")
st.caption(f"Versão {oraculo.__version__}")

# Container principal para evitar reruns desnecessários
with st.container():
    tab1, tab2 = st.tabs(["Consultar", "Histórico"])
    
    with tab1:
        with st.form(key="form_pergunta"):
            pergunta = st.text_area("Faça sua pergunta ao oráculo:")
            arquivo = st.file_uploader("Anexar arquivo (PDF/DOCX)", type=["pdf", "docx"])
            enviar = st.form_submit_button("Consultar")
            
            if enviar and pergunta:
                with st.spinner("O oráculo está refletindo..."):
                    try:
                        resultado = oraculo.processar_pergunta(pergunta, arquivo)
                        st.success("Resposta do oráculo:")
                        st.markdown(f"> {resultado['resposta']}")
                    except Exception as e:
                        st.error(f"Erro ao consultar o oráculo: {str(e)}")
                        st.stop()
    
    with tab2:
        st.subheader("Últimas consultas")
        historico = oraculo.historico(limit=10)
        
        if not historico:
            st.info("Nenhuma consulta registrada ainda")
        else:
            for item in historico:
                with st.expander(f"Consulta #{item['id']} - {item['data'][:10]}"):
                    st.markdown(f"**Pergunta:** {item['pergunta']}")
                    if item['arquivo']:
                        st.caption(f"Arquivo anexado: {Path(item['arquivo']).name}")
                    st.markdown(f"**Resposta:** {item['resposta']}")
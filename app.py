#!/usr/bin/env python3
"""
Streamlit App para o Oráculo Sábio
"""
import streamlit as st
from oraculo import Oraculo, __version__  # Importação correta da versão
import traceback
from pathlib import Path

# Configuração inicial com tratamento de eros
try:
    # Configuração da página
    st.set_page_config(
        page_title="🔮 Oráculo Sábio",
        page_icon="🔮",
        layout="centered"
    )
    
    # Exibe a versão corretamente importada do módulo
    st.sidebar.caption(f"Versão {__version__}")
    
    # Inicialização segura do oráculo
    @st.cache_resource
    def carregar_oraculo():
        try:
            return Oraculo()
        except Exception as e:
            st.error(f"Falha ao iniciar o oráculo: {str(e)}")
            st.code(traceback.format_exc())
            st.stop()
    
    oraculo = carregar_oraculo()

    # Interface principal
    st.title("🔮 Oráculo Sábio")
    st.markdown("Faça sua pergunta ao oráculo e receba sabedoria ancestral.")
    
    # Container principal
    with st.container():
        tab1, tab2 = st.tabs(["Consultar", "Histórico"])
        
        with tab1:
            with st.form(key="form_pergunta"):
                pergunta = st.text_area("Sua pergunta:", height=150)
                arquivo = st.file_uploader(
                    "Anexar contexto (PDF/DOCX)",
                    type=["pdf", "docx"],
                    help="Documentos para contextualizar sua pergunta"
                )
                enviar = st.form_submit_button("Consultar 🔍")
                
                if enviar and pergunta:
                    with st.spinner("O oráculo está meditando..."):
                        try:
                            resultado = oraculo.processar_pergunta(pergunta, arquivo)
                            st.success("Resposta do oráculo:")
                            st.markdown(f"```\n{resultado['resposta']}\n```")
                            st.caption(f"ID da consulta: #{resultado['id']}")
                        except Exception as e:
                            st.error(f"Erro na consulta: {str(e)}")
                            st.code(traceback.format_exc())
        
        with tab2:
            st.subheader("Últimas consultas")
            try:
                historico = oraculo.historico(limit=10)
                
                if not historico:
                    st.info("Nenhuma consulta registrada")
                else:
                    for item in historico:
                        with st.expander(f"Consulta #{item['id']} - {item['data'][:10]}"):
                            st.markdown(f"**❓ Pergunta:**\n{item['pergunta']}")
                            if item['arquivo']:
                                st.caption(f"📎 Anexo: {Path(item['arquivo']).name}")
                            st.markdown(f"**🔮 Resposta:**\n{item['resposta']}")
            except Exception as e:
                st.error(f"Erro ao carregar histórico: {str(e)}")

except Exception as e:
    st.error(f"ERRO CRÍTICO NO APLICATIVO")
    st.code(traceback.format_exc())
    st.error("Por favor, recarregue a página ou tente novamente mais tarde.")
       

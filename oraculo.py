#!/usr/bin/env python3
"""
Módulo Oráculo - Sistema de perguntas e respostas com integração OpenAI
Versão otimizada para deploy no Streamlit Cloud
"""

__version__ = "1.0.0-cloud"

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
import traceback
from openai import OpenAI

# Verificação do ambiente
print(f"Python {sys.version}")
print(f"OpenAI {openai.__version__}")
print(f"Arquivo openai: {openai.__file__}")

# Remoção de variáveis de ambiente que podem interferir
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

# Configuração inicial para evitar erros no Streamlit Cloud
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    logging.warning(f"Erro ao carregar dotenv: {str(e)}")

# Configuração de pastas (ajustado para cloud)
DATA_FOLDER = Path(__file__).parent / "data"
UPLOAD_FOLDER = Path(__file__).parent / "uploads"

# Criação de pastas segura
try:
    DATA_FOLDER.mkdir(exist_ok=True)
    UPLOAD_FOLDER.mkdir(exist_ok=True)
except Exception as e:
    logging.error(f"Erro ao criar pastas: {str(e)}")

# Configuração de logging otimizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_FOLDER/'oraculo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('oraculo')

class BancoDeDados:
    """Versão otimizada para cloud com tratamento de erros"""
    
    def __init__(self):
        self.arquivo = DATA_FOLDER / "perguntas.json"
        self.dados = {"perguntas": []}
        self._carregar()

    def _carregar(self):
        try:
            if self.arquivo.exists():
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    self.dados = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}")
            self.dados = {"perguntas": []}

    def salvar(self):
        try:
            with open(self.arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.dados, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados: {str(e)}")
            return False

    def adicionar_pergunta(self, pergunta, contexto=None):
        registro = {
            "id": len(self.dados["perguntas"]) + 1,
            "pergunta": pergunta,
            "contexto": contexto,
            "resposta": None,
            "data": datetime.now().isoformat(),
            "respondida": False
        }
        self.dados["perguntas"].append(registro)
        return registro if self.salvar() else None

    def responder_pergunta(self, id_pergunta, resposta):
        for item in self.dados["perguntas"]:
            if item["id"] == id_pergunta:
                item.update({
                    "resposta": resposta,
                    "respondida": True,
                    "data_resposta": datetime.now().isoformat()
                })
                return self.salvar()
        return False

class GerenciadorIA:
    """Classe com tratamento robusto para falhas na API"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self._inicializar_cliente()
    
    def _inicializar_cliente(self):
        if not self.api_key:
            logger.warning("Chave OpenAI não configurada")
            return None

        try:
            # Inicialização segura e moderna
            self.client = OpenAI(
                api_key=self.api_key,
                _strict_response_validation=True  # Modo estrito
            )
            logger.info("Cliente OpenAI inicializado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Falha crítica na inicialização: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            traceback.print_exc()
            return False
    
    def gerar_resposta(self, pergunta, contexto=None):
        if not self.client:
            return "⚠️ Serviço indisponível (configuração incompleta)"

        try:
            messages = [{
                "role": "system",
                "content": "Você é um oráculo sábio que fornece conselhos precisos."
            }]
            
            if contexto:
                messages.append({
                    "role": "system",
                    "content": f"Contexto adicional: {contexto}"
                })
                
            messages.append({
                "role": "user",
                "content": pergunta
            })

            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_IA", "gpt-3.5-turbo-0125"),
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {str(e)}")
            return "🔮 O oráculo está temporariamente indisponível"

class Oraculo:
    """Classe principal com proteção contra erros no Streamlit"""
    
    def __init__(self):
        self.db = BancoDeDados()
        self.ia = GerenciadorIA()
        self._configurar_ambiente()

    def _configurar_ambiente(self):
        """Prepara o ambiente para execução no Streamlit Cloud"""
        try:
            import streamlit as st
            st.set_page_config(
                page_title="Oráculo Sábio",
                page_icon="🔮",
                layout="centered"
            )
        except:
            pass

    def processar_pergunta(self, pergunta, contexto=None):
        try:
            registro = self.db.adicionar_pergunta(pergunta, contexto)
            if not registro:
                return {"erro": "Falha ao registrar pergunta"}
                
            resposta = self.ia.gerar_resposta(pergunta, contexto)
            if not self.db.responder_pergunta(registro["id"], resposta):
                return {"erro": "Falha ao registrar resposta"}
                
            return registro
        except Exception as e:
            logger.critical(f"Erro no processamento: {str(e)}")
            return {"erro": f"Falha crítica: {str(e)}"}

def main():
    """Interface principal para o Streamlit"""
    import streamlit as st
    
    oraculo = Oraculo()
    st.title("🔮 Oráculo Sábio")
    
    with st.form("pergunta_form"):
        pergunta = st.text_area("Faça sua pergunta ao oráculo:")
        contexto = st.text_input("Contexto adicional (opcional):")
        submitted = st.form_submit_button("Enviar")
        
        if submitted and pergunta:
            with st.spinner("Consultando o oráculo..."):
                resultado = oraculo.processar_pergunta(pergunta, contexto)
                if "erro" in resultado:
                    st.error(resultado["erro"])
                else:
                    st.success(resultado.get("resposta", "Sem resposta"))

# Garante que a interface roda no Streamlit Cloud
if "streamlit" in __import__("sys").modules:
    main()

# Interface segura para execução local
if __name__ == "__main__":
    print(f"=== ORÁCULO SÁBIO (v{__version__}) ===")
    print("Modo local ativado (digite 'sair' para encerrar)\n")
    
    oraculo = Oraculo()
    
    try:
        while True:
            pergunta = input("Pergunta: ").strip()
            if pergunta.lower() == 'sair':
                break
                
            resultado = oraculo.processar_pergunta(pergunta)
            print(f"\nResposta: {resultado.get('resposta', '[sem resposta]')}\n")
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário")
    except Exception as e:
        logger.critical(f"Erro fatal: {str(e)}")

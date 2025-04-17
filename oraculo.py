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
import openai
# Ensure OpenAI class is imported correctly
from openai import OpenAI

# Verificação do ambiente
print(f"Python {sys.version}")
print(f"OpenAI {openai.__version__}")
print(f"Arquivo openai: {openai.__file__}")

# Remoção de variáveis de ambiente que podem interferir
# (Good practice, especially in cloud environments)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

# Configuração inicial para evitar erros no Streamlit Cloud
try:
    # Attempt to load environment variables from .env file if present
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not installed, log a warning but continue
    logging.warning("dotenv not installed, skipping .env file loading.")
except Exception as e:
    # Log other potential errors during dotenv loading
    logging.warning(f"Erro ao carregar dotenv: {str(e)}")

# Configuração de pastas (ajustado para cloud)
# Use Path objects for better path manipulation
DATA_FOLDER = Path(__file__).parent / "data"
UPLOAD_FOLDER = Path(__file__).parent / "uploads"

# Criação de pastas segura
try:
    DATA_FOLDER.mkdir(parents=True, exist_ok=True) # Add parents=True
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True) # Add parents=True
except Exception as e:
    logging.error(f"Erro ao criar pastas: {str(e)}")

# Configuração de logging otimizada
# Log to both file and console stream
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_FOLDER/'oraculo.log', encoding='utf-8'), # Specify encoding
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
        """Loads data from the JSON file."""
        try:
            if self.arquivo.exists() and self.arquivo.stat().st_size > 0: # Check if file is not empty
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    self.dados = json.load(f)
                    # Ensure 'perguntas' key exists and is a list
                    if "perguntas" not in self.dados or not isinstance(self.dados["perguntas"], list):
                        logger.warning(f"Formato inválido no arquivo {self.arquivo}. Reiniciando com lista vazia.")
                        self.dados = {"perguntas": []}
            else:
                 # If file doesn't exist or is empty, initialize with empty list
                 self.dados = {"perguntas": []}
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON de {self.arquivo}: {str(e)}. Reiniciando com lista vazia.")
            self.dados = {"perguntas": []}
        except Exception as e:
            logger.error(f"Erro inesperado ao carregar dados de {self.arquivo}: {str(e)}")
            # Fallback to empty list in case of other errors
            self.dados = {"perguntas": []}


    def salvar(self):
        """Saves the current data to the JSON file."""
        try:
            # Ensure the parent directory exists before writing
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            with open(self.arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.dados, f, indent=2, ensure_ascii=False)
            logger.info(f"Dados salvos com sucesso em {self.arquivo}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados em {self.arquivo}: {str(e)}")
            return False

    def adicionar_pergunta(self, pergunta, contexto=None):
        """Adds a new question record."""
        try:
            # Find the next ID safely
            next_id = max([p.get("id", 0) for p in self.dados.get("perguntas", [])] + [0]) + 1
            registro = {
                "id": next_id,
                "pergunta": pergunta,
                "contexto": contexto,
                "resposta": None,
                "data": datetime.now().isoformat(),
                "respondida": False
            }
            # Ensure 'perguntas' list exists before appending
            if "perguntas" not in self.dados:
                self.dados["perguntas"] = []
            self.dados["perguntas"].append(registro)
            logger.info(f"Pergunta adicionada (ID: {next_id}): {pergunta[:50]}...")
            return registro if self.salvar() else None
        except Exception as e:
            logger.error(f"Erro ao adicionar pergunta: {str(e)}")
            return None


    def responder_pergunta(self, id_pergunta, resposta):
        """Updates a question record with its answer."""
        try:
            found = False
            for item in self.dados.get("perguntas", []):
                if item.get("id") == id_pergunta:
                    item.update({
                        "resposta": resposta,
                        "respondida": True,
                        "data_resposta": datetime.now().isoformat()
                    })
                    found = True
                    break
            if found:
                logger.info(f"Pergunta respondida (ID: {id_pergunta})")
                return self.salvar()
            else:
                logger.warning(f"Tentativa de responder pergunta não encontrada (ID: {id_pergunta})")
                return False
        except Exception as e:
            logger.error(f"Erro ao responder pergunta (ID: {id_pergunta}): {str(e)}")
            return False


class GerenciadorIA:
    """Classe com tratamento robusto para falhas na API"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Initializes the OpenAI client."""
        if not self.api_key:
            # Log a clear warning if the API key is missing
            logger.warning("Chave API da OpenAI (OPENAI_API_KEY) não encontrada nas variáveis de ambiente.")
            return False # Indicate failure clearly

        try:
            # --- CORREÇÃO APLICADA AQUI ---
            # Initialize the client with only the necessary api_key.
            # The 'proxies' argument is not valid in recent versions.
            # Removed '_strict_response_validation=True' as it's internal.
            self.client = OpenAI(
                api_key=self.api_key
                # If proxies ARE needed, configure them via http_client:
                # import httpx
                # proxy_url = os.getenv("HTTPS_PROXY") # or HTTP_PROXY
                # if proxy_url:
                #     proxies = {"http://": proxy_url, "https://": proxy_url}
                #     http_client = httpx.Client(proxies=proxies)
                # else:
                #     http_client = None # Use default httpx client
                # self.client = OpenAI(api_key=self.api_key, http_client=http_client)
            )
            # --- FIM DA CORREÇÃO ---
            logger.info("Cliente OpenAI inicializado com sucesso.")
            # Optional: Add a simple test call to verify connection
            # try:
            #     self.client.models.list()
            #     logger.info("Conexão com a API OpenAI verificada.")
            # except Exception as api_err:
            #     logger.error(f"Falha ao verificar conexão com API OpenAI: {api_err}")
            #     self.client = None # Reset client if verification fails
            #     return False
            return True # Indicate success
        except Exception as e:
            # Log detailed error information during initialization
            logger.error(f"Falha crítica na inicialização do cliente OpenAI: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            # Log the traceback for debugging
            logger.error(traceback.format_exc())
            self.client = None # Ensure client is None if init fails
            return False # Indicate failure

    def gerar_resposta(self, pergunta, contexto=None):
        """Generates a response using the OpenAI API."""
        if not self.client:
            # Return a user-friendly message if the client isn't ready
            logger.warning("Tentativa de gerar resposta sem cliente OpenAI inicializado.")
            return "⚠️ Serviço de IA indisponível no momento (falha na inicialização ou configuração)."

        try:
            # Construct the messages list for the chat completion
            messages = [{
                "role": "system",
                "content": "Você é um oráculo sábio que fornece conselhos precisos e ponderados." # Refined prompt
            }]

            if contexto:
                # Add context if provided
                messages.append({
                    "role": "system",
                    "content": f"Contexto adicional fornecido: {contexto}"
                })

            # Add the user's question
            messages.append({
                "role": "user",
                "content": pergunta
            })

            # Call the OpenAI API
            logger.info(f"Enviando pergunta para OpenAI: {pergunta[:50]}...")
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_IA", "gpt-3.5-turbo"), # Default to gpt-3.5-turbo if not set
                messages=messages,
                temperature=float(os.getenv("IA_TEMPERATURE", 0.7)), # Allow configuring temperature
                max_tokens=int(os.getenv("IA_MAX_TOKENS", 500)), # Allow configuring max tokens
                # Consider adding timeout: timeout=30.0
            )
            # Extract the response content
            resposta_ia = response.choices[0].message.content.strip()
            logger.info("Resposta recebida da OpenAI.")
            return resposta_ia
        except openai.APIConnectionError as e:
             logger.error(f"Erro de conexão com a API OpenAI: {e}")
             return "🔮 O oráculo não conseguiu se conectar aos reinos etéreos. Verifique sua conexão."
        except openai.RateLimitError as e:
             logger.error(f"Erro de limite de taxa da API OpenAI: {e}")
             return "🔮 O oráculo está sobrecarregado no momento. Tente novamente mais tarde."
        except openai.APIStatusError as e:
             logger.error(f"Erro de status da API OpenAI: Status={e.status_code}, Resposta={e.response}")
             return f"🔮 O oráculo encontrou um problema inesperado (Erro {e.status_code}). Tente novamente."
        except Exception as e:
            # Catch other potential errors during API call
            logger.error(f"Erro inesperado na geração de resposta da IA: {str(e)}")
            logger.error(traceback.format_exc())
            return "🔮 O oráculo está temporariamente confuso e não pôde responder. Tente novamente."

class Oraculo:
    """Classe principal com proteção contra erros no Streamlit"""

    def __init__(self):
        logger.info("Inicializando o Oráculo...")
        self.db = BancoDeDados()
        self.ia = GerenciadorIA()
        # No need for _configurar_ambiente here, Streamlit handles its setup
        logger.info("Oráculo inicializado.")


    def processar_pergunta(self, pergunta, contexto=None):
        """Processes a question: saves it, gets an answer from AI, saves the answer."""
        if not pergunta or not isinstance(pergunta, str) or not pergunta.strip():
             logger.warning("Tentativa de processar pergunta vazia ou inválida.")
             return {"erro": "A pergunta não pode estar vazia."}

        logger.info(f"Processando pergunta: {pergunta[:50]}...")
        try:
            # 1. Add question to DB
            registro = self.db.adicionar_pergunta(pergunta, contexto)
            if not registro:
                logger.error("Falha ao registrar a pergunta no banco de dados.")
                return {"erro": "Desculpe, houve uma falha ao registrar sua pergunta."}

            # 2. Generate answer using AI
            resposta = self.ia.gerar_resposta(pergunta, contexto)
            # Update the record with the answer immediately (even if saving fails later)
            registro["resposta"] = resposta

            # 3. Save answer to DB
            if not self.db.responder_pergunta(registro["id"], resposta):
                logger.error(f"Falha ao salvar a resposta para a pergunta ID {registro['id']} no banco de dados.")
                # Return the result anyway, but log the saving error
                return {"aviso": "Sua resposta foi gerada, mas houve um problema ao salvá-la permanentemente.", **registro}

            logger.info(f"Pergunta ID {registro['id']} processada com sucesso.")
            return registro # Return the complete record including the answer

        except Exception as e:
            # Catch unexpected errors during the processing flow
            logger.critical(f"Erro crítico durante o processamento da pergunta: {str(e)}")
            logger.critical(traceback.format_exc())
            return {"erro": f"Ocorreu uma falha crítica inesperada ao processar sua pergunta."}

# --- Streamlit Interface ---
def main_streamlit():
    """Main function to run the Streamlit interface."""
    try:
        import streamlit as st
    except ImportError:
        logger.error("Streamlit não está instalado. A interface gráfica não pode ser iniciada.")
        print("Erro: Streamlit não está instalado. Execute 'pip install streamlit' para usar a interface gráfica.")
        return # Exit if streamlit is not available

    # Initialize Oraculo only once using Streamlit's session state
    if 'oraculo_instance' not in st.session_state:
        st.session_state.oraculo_instance = Oraculo()

    oraculo = st.session_state.oraculo_instance

    st.set_page_config(
        page_title="Oráculo Sábio",
        page_icon="🔮",
        layout="centered"
    )

    st.title("🔮 Oráculo Sábio")
    st.caption(f"v{__version__}")

    # Use st.form for better control over submission
    with st.form("pergunta_form", clear_on_submit=True): # Clear form after submission
        pergunta = st.text_area("Faça sua pergunta ao oráculo:", height=100, key="pergunta_input")
        contexto = st.text_input("Contexto adicional (opcional):", key="contexto_input")
        submitted = st.form_submit_button("Consultar o Oráculo")

        if submitted:
            if not pergunta or not pergunta.strip():
                st.warning("Por favor, digite sua pergunta antes de consultar.")
            else:
                with st.spinner("Consultando os ventos do conhecimento..."):
                    # Process the question using the Oraculo instance
                    resultado = oraculo.processar_pergunta(pergunta.strip(), contexto.strip() if contexto else None)

                # Display result or error
                if "erro" in resultado:
                    st.error(f"Erro: {resultado['erro']}")
                elif "aviso" in resultado:
                     st.warning(f"Aviso: {resultado['aviso']}")
                     st.info("Sua resposta:")
                     st.markdown(resultado.get("resposta", "*O oráculo ficou em silêncio...*")) # Display answer even with warning
                elif "resposta" in resultado:
                    st.success("O Oráculo respondeu:")
                    st.markdown(resultado.get("resposta", "*O oráculo ficou em silêncio...*")) # Use markdown for better formatting
                else:
                    st.error("Ocorreu uma resposta inesperada do Oráculo.") # Fallback for unexpected structure


# --- Local Console Interface ---
def main_local():
    """Main function to run the local console interface."""
    print(f"\n=== ORÁCULO SÁBIO (Modo Console v{__version__}) ===")
    print("Conectando ao Oráculo...")
    try:
        oraculo = Oraculo()
        if not oraculo.ia.client:
             print("\n⚠️ Aviso: Cliente OpenAI não inicializado. Verifique a chave API e a conexão.")

        print("\nOráculo pronto. Digite sua pergunta ou 'sair' para encerrar.")

        while True:
            try:
                pergunta = input("\nSua Pergunta: ").strip()
                if pergunta.lower() == 'sair':
                    print("\nAté a próxima consulta!")
                    break
                if not pergunta:
                    continue # Ask again if input is empty

                contexto = input("Contexto (opcional, deixe em branco se não houver): ").strip()

                print("\nConsultando...")
                resultado = oraculo.processar_pergunta(pergunta, contexto if contexto else None)

                if "erro" in resultado:
                    print(f"\nErro: {resultado['erro']}")
                elif "aviso" in resultado:
                    print(f"\nAviso: {resultado['aviso']}")
                    print(f"\nResposta do Oráculo:\n{resultado.get('resposta', '[Sem resposta]')}")
                elif "resposta" in resultado:
                     print(f"\nResposta do Oráculo:\n{resultado.get('resposta', '[Sem resposta]')}")
                else:
                     print("\nErro: Resposta inesperada recebida.")

            except EOFError: # Handle Ctrl+D
                 print("\nEncerrado pelo usuário (EOF).")
                 break
            except KeyboardInterrupt: # Handle Ctrl+C
                print("\nEncerrado pelo usuário (Ctrl+C).")
                break

    except Exception as e:
        # Catch critical errors during local execution setup or loop
        logger.critical(f"Erro fatal no modo console: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"\nErro crítico: {e}")


# --- Main Execution Logic ---
if __name__ == "__main__":
    # Check if running under Streamlit based on module import
    # This is a common way to detect Streamlit execution context
    if "streamlit" in sys.modules and hasattr(sys, 'argv') and 'streamlit' in sys.argv[0]:
         logger.info("Executando no modo Streamlit.")
         main_streamlit()
    else:
         logger.info("Executando no modo console local.")
         main_local()



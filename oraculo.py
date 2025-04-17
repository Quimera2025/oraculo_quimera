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
# --- ADICIONADO: Importar httpx ---
import httpx
# --- FIM DA ADIÇÃO ---


# Verificação do ambiente
print(f"Python {sys.version}")
print(f"OpenAI {openai.__version__}")
print(f"Arquivo openai: {openai.__file__}")
# Add httpx version for debugging
try:
    import httpx
    print(f"httpx {httpx.__version__}")
except ImportError:
    print("httpx não está instalado.")


# Remoção de variáveis de ambiente que podem interferir
# (Good practice, especially in cloud environments)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
# Also remove lowercase versions just in case
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)

# Configuração inicial para evitar erros no Streamlit Cloud
try:
    # Attempt to load environment variables from .env file if present
    from dotenv import load_dotenv
    load_dotenv()
    logger.info(".env file loaded if present.") # Log success
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
    # Use logger here as it might be configured already
    logging.error(f"Erro ao criar pastas: {str(e)}")

# Configuração de logging otimizada
# Log to both file and console stream
log_file_path = DATA_FOLDER / 'oraculo.log'
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # Added logger name
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'), # Specify encoding
            logging.StreamHandler(sys.stdout) # Log to stdout
        ]
    )
    # Define logger after basicConfig
    logger = logging.getLogger('oraculo')
    logger.info(f"Logging configurado. Arquivo de log: {log_file_path}")
except Exception as log_err:
     # Fallback logging if file handler fails
     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
     logger = logging.getLogger('oraculo')
     logger.error(f"Erro ao configurar logging para arquivo {log_file_path}: {log_err}. Usando apenas console.")


class BancoDeDados:
    """Versão otimizada para cloud com tratamento de erros"""
    # Uses the logger defined globally
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
                 logger.info(f"Arquivo {self.arquivo} não encontrado ou vazio. Iniciando com lista vazia.")
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
            # logger.info(f"Dados salvos com sucesso em {self.arquivo}") # Reduce log noise maybe
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
        """Initializes the OpenAI client, explicitly providing an httpx client."""
        if not self.api_key:
            # Log a clear warning if the API key is missing
            logger.warning("Chave API da OpenAI (OPENAI_API_KEY) não encontrada nas variáveis de ambiente.")
            return False # Indicate failure clearly

        try:
            # --- CORREÇÃO APLICADA AQUI (Tentativa 2) ---
            # 1. Explicitly create an httpx client instance.
            #    We create a basic one *without* proxies, as the goal is to avoid
            #    the problematic 'proxies' argument being passed internally.
            logger.info("Criando cliente HTTPX explícito...")
            custom_http_client = httpx.Client(
                 # Explicitly disable proxy lookup from environment if needed,
                 # although removing env vars should be sufficient.
                 # proxies=None, # Uncomment if removing env vars doesn't work
                 # http2=True, # Enable HTTP/2 if desired
                 # timeout=30.0 # Set a default timeout
            )
            logger.info("Cliente HTTPX criado.")

            # 2. Pass the custom httpx client to the OpenAI constructor.
            logger.info("Inicializando cliente OpenAI com cliente HTTPX customizado...")
            self.client = OpenAI(
                api_key=self.api_key,
                http_client=custom_http_client # Pass the explicitly created client
            )
            # --- FIM DA CORREÇÃO ---

            logger.info("Cliente OpenAI inicializado com sucesso usando HTTPX customizado.")

            # Optional: Add a simple test call to verify connection
            try:
                 logger.info("Verificando conexão com a API OpenAI...")
                 self.client.models.list(timeout=10) # Add timeout to verification
                 logger.info("Conexão com a API OpenAI verificada com sucesso.")
            except Exception as api_err:
                 logger.error(f"Falha ao verificar conexão com API OpenAI: {api_err}")
                 # Decide if this should be fatal for initialization
                 # self.client = None # Reset client if verification fails?
                 # return False
                 logger.warning("Não foi possível verificar a conexão, mas a inicialização do cliente continua.")


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
            # Use configured model, temperature, max_tokens from env vars or defaults
            model = os.getenv("MODEL_IA", "gpt-3.5-turbo")
            temperature = float(os.getenv("IA_TEMPERATURE", 0.7))
            max_tokens = int(os.getenv("IA_MAX_TOKENS", 500))
            api_timeout = float(os.getenv("IA_API_TIMEOUT", 30.0)) # Add configurable timeout

            logger.info(f"Usando modelo={model}, temp={temperature}, max_tokens={max_tokens}, timeout={api_timeout}s")

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=api_timeout # Pass timeout to the API call
            )
            # Extract the response content
            resposta_ia = response.choices[0].message.content.strip()
            logger.info("Resposta recebida da OpenAI.")
            return resposta_ia
        # More specific error handling based on openai exceptions
        except openai.APIConnectionError as e:
             logger.error(f"Erro de conexão com a API OpenAI: {e}")
             return "🔮 O oráculo não conseguiu se conectar aos reinos etéreos. Verifique sua conexão de rede ou as configurações de proxy (se aplicável)."
        except openai.RateLimitError as e:
             logger.error(f"Erro de limite de taxa da API OpenAI: {e}")
             return "🔮 O oráculo está sobrecarregado no momento devido a muitas consultas. Tente novamente mais tarde."
        except openai.AuthenticationError as e:
             logger.error(f"Erro de autenticação da API OpenAI: {e}")
             return "🔮 A chave de acesso do Oráculo (API Key) é inválida ou expirou. Verifique a configuração OPENAI_API_KEY."
        except openai.PermissionDeniedError as e:
             logger.error(f"Erro de permissão da API OpenAI: {e}")
             return "🔮 O Oráculo não tem permissão para acessar este recurso. Verifique as permissões da sua chave API."
        except openai.NotFoundError as e:
             logger.error(f"Erro 'Não Encontrado' da API OpenAI (possivelmente modelo inválido): {e}")
             return f"🔮 O Oráculo não encontrou o recurso solicitado (talvez o modelo '{os.getenv('MODEL_IA', 'gpt-3.5-turbo')}' seja inválido?)."
        except openai.UnprocessableEntityError as e:
             logger.error(f"Erro 'Unprocessable Entity' da API OpenAI (possivelmente entrada inválida): {e}")
             return "🔮 O Oráculo não entendeu a solicitação devido a um formato inválido. Verifique a pergunta ou contexto."
        except openai.APIStatusError as e:
             logger.error(f"Erro de status da API OpenAI: Status={e.status_code}, Resposta={e.response}")
             return f"🔮 O oráculo encontrou um problema inesperado ao se comunicar com os reinos superiores (Erro {e.status_code}). Tente novamente."
        except openai.APITimeoutError as e:
             logger.error(f"Timeout ao chamar a API OpenAI: {e}")
             return "🔮 A consulta ao Oráculo demorou demais para responder. Tente novamente ou simplifique sua pergunta."
        except Exception as e:
            # Catch other potential errors during API call
            logger.error(f"Erro inesperado na geração de resposta da IA: {str(e)}")
            logger.error(traceback.format_exc())
            return "🔮 O oráculo está temporariamente confuso e não pôde responder devido a um erro inesperado. Tente novamente."

class Oraculo:
    """Classe principal com proteção contra erros no Streamlit"""

    def __init__(self):
        logger.info("Inicializando o Oráculo...")
        self.db = BancoDeDados()
        self.ia = GerenciadorIA()
        # Check if IA client initialized successfully
        if not self.ia.client:
             logger.error("Falha ao inicializar o GerenciadorIA. O Oráculo pode não funcionar corretamente.")
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

            # 2. Generate answer using AI (Check if IA is available first)
            if not self.ia.client:
                 logger.error("Tentativa de gerar resposta, mas o cliente IA não está inicializado.")
                 resposta = "⚠️ Serviço de IA indisponível no momento."
                 # Still try to save the question with the error message as response
                 self.db.responder_pergunta(registro["id"], resposta)
                 registro["resposta"] = resposta # Update record in memory
                 return {"erro": resposta, **registro} # Return error but include record

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
    # This prevents re-initialization on every interaction
    if 'oraculo_instance' not in st.session_state:
        logger.info("Criando nova instância do Oraculo para a sessão Streamlit.")
        with st.spinner("Iniciando o Oráculo... Por favor, aguarde."):
            st.session_state.oraculo_instance = Oraculo()
        logger.info("Instância do Oraculo criada e armazenada no estado da sessão.")


    oraculo = st.session_state.oraculo_instance

    st.set_page_config(
        page_title="Oráculo Sábio",
        page_icon="🔮",
        layout="centered"
    )

    st.title("🔮 Oráculo Sábio")
    st.caption(f"v{__version__}")

    # Display warning if IA client failed to initialize
    if not oraculo.ia.client:
        st.warning("⚠️ O serviço de IA não pôde ser inicializado. Verifique a chave da API OpenAI e a conexão de rede. As respostas não estarão disponíveis.", icon="🚨")


    # Use st.form for better control over submission
    with st.form("pergunta_form", clear_on_submit=True): # Clear form after submission
        pergunta = st.text_area("Faça sua pergunta ao oráculo:", height=100, key="pergunta_input", disabled=(not oraculo.ia.client)) # Disable if IA not ready
        contexto = st.text_input("Contexto adicional (opcional):", key="contexto_input", disabled=(not oraculo.ia.client)) # Disable if IA not ready
        submitted = st.form_submit_button("Consultar o Oráculo", disabled=(not oraculo.ia.client)) # Disable if IA not ready

        if submitted:
            if not pergunta or not pergunta.strip():
                st.warning("Por favor, digite sua pergunta antes de consultar.")
            else:
                with st.spinner("Consultando os ventos do conhecimento..."):
                    # Process the question using the Oraculo instance
                    resultado = oraculo.processar_pergunta(pergunta.strip(), contexto.strip() if contexto else None)

                # Display result or error
                if "erro" in resultado:
                    st.error(f"{resultado['erro']}") # Simpler error display
                elif "aviso" in resultado:
                     st.warning(f"{resultado['aviso']}")
                     st.info("Sua resposta:")
                     st.markdown(resultado.get("resposta", "*O oráculo ficou em silêncio...*")) # Display answer even with warning
                elif "resposta" in resultado:
                    # st.success("O Oráculo respondeu:") # Maybe too verbose
                    st.markdown(f"**Resposta do Oráculo:**\n\n{resultado.get('resposta', '*O oráculo ficou em silêncio...*')}") # Use markdown for better formatting
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
             print("\n⚠️ Aviso: Cliente OpenAI não pôde ser inicializado. Verifique a chave API (OPENAI_API_KEY) e a conexão de rede.")
             print("   As funcionalidades que dependem da IA não estarão disponíveis.")
        else:
             print("\nOráculo pronto.")

        print("\nDigite sua pergunta ou 'sair' para encerrar.")

        while True:
            try:
                pergunta = input("\nSua Pergunta: ").strip()
                if pergunta.lower() == 'sair':
                    print("\nAté a próxima consulta!")
                    break
                if not pergunta:
                    continue # Ask again if input is empty

                if not oraculo.ia.client:
                     print("   -> Cliente IA indisponível. Não é possível processar a pergunta.")
                     continue

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
        print(f"\nErro crítico encontrado: {e}")
        print("Verifique o arquivo de log para mais detalhes.")


# --- Main Execution Logic ---
if __name__ == "__main__":
    # Check if running under Streamlit based on module import and argv
    # This is a common way to detect Streamlit execution context
    is_streamlit = False
    if "streamlit" in sys.modules:
        try:
            # A more robust check for Streamlit execution
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx():
                is_streamlit = True
        except Exception:
            # Fallback check if the above fails (e.g., older Streamlit versions)
             if hasattr(sys, 'argv') and 'streamlit' in sys.argv[0]:
                 is_streamlit = True


    if is_streamlit:
         logger.info("Executando no modo Streamlit.")
         main_streamlit()
    else:
         logger.info("Executando no modo console local.")
         main_local()



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
# Import httpx
import httpx
# Import Streamlit (conditionally if needed, but good practice to have it top-level if used)
try:
    import streamlit as st
except ImportError:
    st = None # Assign None if streamlit is not installed


# --- Configuração de Pastas ---
# Use Path objects for better path manipulation
# Define DATA_FOLDER relative to the script file location
try:
    # Get the directory containing the script file
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:
     # Fallback for environments where __file__ is not defined (e.g., some notebooks)
     SCRIPT_DIR = Path.cwd()

DATA_FOLDER = SCRIPT_DIR / "data"
UPLOAD_FOLDER = SCRIPT_DIR / "uploads"

# --- Criação de Pastas Segura ---
try:
    DATA_FOLDER.mkdir(parents=True, exist_ok=True) # Add parents=True
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True) # Add parents=True
except Exception as e:
    # Use basic print here as logger might not be configured yet
    print(f"[ERROR] Erro ao criar pastas: {str(e)}", file=sys.stderr)

# --- Configuração de Logging Otimizada ---
log_file_path = DATA_FOLDER / 'oraculo.log'
log_handlers = []
try:
    # File Handler
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    log_handlers.append(file_handler)
except Exception as log_file_err:
     print(f"[WARNING] Erro ao configurar logging para arquivo {log_file_path}: {log_file_err}. Log de arquivo desativado.", file=sys.stderr)

# Console Handler (always add)
stream_handler = logging.StreamHandler(sys.stdout)
log_handlers.append(stream_handler)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # Added logger name
    handlers=log_handlers
)
logger = logging.getLogger('oraculo') # Define logger *after* basicConfig
logger.info(f"Logging configurado. Arquivo de log: {'Ativado' if file_handler in log_handlers else 'Desativado'}")


# --- Carregamento de Variáveis de Ambiente (dotenv) ---
# Moved AFTER logger setup
try:
    from dotenv import load_dotenv
    dotenv_path = SCRIPT_DIR / '.env' # Look for .env in the script directory
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Arquivo .env carregado de {dotenv_path}")
    else:
        logger.info("Arquivo .env não encontrado, pulando carregamento.")
except ImportError:
    logger.warning("dotenv não instalado, skipping .env file loading.")
except Exception as e:
    logger.warning(f"Erro ao carregar dotenv: {str(e)}")


# --- Verificação do Ambiente ---
logger.info(f"Python {sys.version}")
logger.info(f"OpenAI {openai.__version__}")
logger.info(f"Arquivo openai: {openai.__file__}")
try:
    logger.info(f"httpx {httpx.__version__}")
except Exception:
     logger.warning("Não foi possível obter a versão do httpx.")
if st:
    try:
        logger.info(f"Streamlit {st.__version__}")
    except Exception:
        logger.warning("Não foi possível obter a versão do Streamlit.")
else:
    logger.info("Streamlit não importado/instalado.")


# --- Remoção de Variáveis de Proxy (Opcional, mas pode ajudar) ---
# Moved after logging setup and dotenv loading
proxies_to_remove = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
for proxy_var in proxies_to_remove:
    if proxy_var in os.environ:
        os.environ.pop(proxy_var, None)
        logger.info(f"Variável de ambiente de proxy removida: {proxy_var}")


# --- Classes Principais ---

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
            logger.warning("Chave API da OpenAI (OPENAI_API_KEY) não encontrada nas variáveis de ambiente.")
            return False # Indicate failure clearly

        try:
            # 1. Explicitly create an httpx client instance.
            logger.info("Criando cliente HTTPX explícito...")
            # Set timeout for the client itself
            connect_timeout = float(os.getenv("HTTPX_CONNECT_TIMEOUT", 10.0))
            read_timeout = float(os.getenv("HTTPX_READ_TIMEOUT", 30.0))
            write_timeout = float(os.getenv("HTTPX_WRITE_TIMEOUT", 30.0))
            pool_timeout = float(os.getenv("HTTPX_POOL_TIMEOUT", 10.0))

            timeouts = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=write_timeout, pool=pool_timeout)

            custom_http_client = httpx.Client(
                # No proxies argument here
                http2=True, # Enable HTTP/2 if desired
                timeout=timeouts # Set default timeouts for the client
            )
            logger.info(f"Cliente HTTPX criado com timeouts: {timeouts}")

            # 2. Pass the custom httpx client to the OpenAI constructor.
            logger.info("Inicializando cliente OpenAI com cliente HTTPX customizado...")
            # Set API call timeout separately if needed, otherwise uses httpx client timeout
            api_timeout_seconds = float(os.getenv("OPENAI_API_TIMEOUT", 60.0)) # e.g., 60 seconds total for API call

            self.client = OpenAI(
                api_key=self.api_key,
                http_client=custom_http_client, # Pass the explicitly created client
                timeout=api_timeout_seconds # Set overall timeout for OpenAI API calls
            )

            logger.info(f"Cliente OpenAI inicializado com sucesso usando HTTPX customizado (Timeout API: {api_timeout_seconds}s).")

            # 3. Optional: Verify connection
            try:
                 logger.info("Verificando conexão com a API OpenAI...")
                 # Use a short timeout for the verification call
                 self.client.models.list(timeout=10)
                 logger.info("Conexão com a API OpenAI verificada com sucesso.")
            except Exception as api_err:
                 logger.error(f"Falha ao verificar conexão com API OpenAI: {api_err}")
                 logger.warning("Não foi possível verificar a conexão, mas a inicialização do cliente continua.")

            return True # Indicate success
        except Exception as e:
            logger.error(f"Falha crítica na inicialização do cliente OpenAI: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            logger.error(traceback.format_exc())
            self.client = None # Ensure client is None if init fails
            return False # Indicate failure

    def gerar_resposta(self, pergunta, contexto=None):
        """Generates a response using the OpenAI API."""
        if not self.client:
            logger.warning("Tentativa de gerar resposta sem cliente OpenAI inicializado.")
            return "⚠️ Serviço de IA indisponível no momento (falha na inicialização ou configuração)."

        try:
            messages = [{
                "role": "system",
                "content": "Você é um oráculo sábio que fornece conselhos precisos e ponderados."
            }]
            if contexto:
                messages.append({
                    "role": "system",
                    "content": f"Contexto adicional fornecido: {contexto}"
                })
            messages.append({
                "role": "user",
                "content": pergunta
            })

            logger.info(f"Enviando pergunta para OpenAI: {pergunta[:50]}...")
            model = os.getenv("MODEL_IA", "gpt-3.5-turbo")
            temperature = float(os.getenv("IA_TEMPERATURE", 0.7))
            max_tokens = int(os.getenv("IA_MAX_TOKENS", 500))
            # Timeout for this specific API call (can override client default)
            # api_call_timeout = float(os.getenv("IA_API_TIMEOUT", 30.0))

            logger.info(f"Usando modelo={model}, temp={temperature}, max_tokens={max_tokens}") # Removed timeout log here as it's set on client

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                # timeout=api_call_timeout # Timeout is now set on the client or OpenAI constructor
            )
            resposta_ia = response.choices[0].message.content.strip()
            logger.info("Resposta recebida da OpenAI.")
            return resposta_ia
        # Specific error handling
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
            logger.error(f"Erro inesperado na geração de resposta da IA: {str(e)}")
            logger.error(traceback.format_exc())
            return "🔮 O oráculo está temporariamente confuso e não pôde responder devido a um erro inesperado. Tente novamente."

class Oraculo:
    """Classe principal com proteção contra erros no Streamlit"""

    def __init__(self):
        logger.info("Inicializando o Oráculo...")
        self.db = BancoDeDados()
        self.ia = GerenciadorIA()
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
                 self.db.responder_pergunta(registro["id"], resposta)
                 registro["resposta"] = resposta # Update record in memory
                 return {"erro": resposta, **registro} # Return error but include record

            resposta = self.ia.gerar_resposta(pergunta, contexto)
            registro["resposta"] = resposta # Update record in memory

            # 3. Save answer to DB
            if not self.db.responder_pergunta(registro["id"], resposta):
                logger.error(f"Falha ao salvar a resposta para a pergunta ID {registro['id']} no banco de dados.")
                return {"aviso": "Sua resposta foi gerada, mas houve um problema ao salvá-la permanentemente.", **registro}

            logger.info(f"Pergunta ID {registro['id']} processada com sucesso.")
            return registro # Return the complete record including the answer

        except Exception as e:
            logger.critical(f"Erro crítico durante o processamento da pergunta: {str(e)}")
            logger.critical(traceback.format_exc())
            return {"erro": f"Ocorreu uma falha crítica inesperada ao processar sua pergunta."}

# --- Streamlit Interface ---
def main_streamlit():
    """Main function to run the Streamlit interface."""
    # Ensure streamlit is available
    if not st:
        logger.error("Streamlit não está instalado ou não pôde ser importado. A interface gráfica não pode ser iniciada.")
        print("Erro: Streamlit não está instalado. Execute 'pip install streamlit' para usar a interface gráfica.")
        return

    # --- CORREÇÃO APLICADA AQUI (Streamlit Error) ---
    # Call set_page_config() as the VERY FIRST Streamlit command.
    st.set_page_config(
        page_title="Oráculo Sábio",
        page_icon="🔮",
        layout="centered"
    )
    # --- FIM DA CORREÇÃO ---

    # Initialize Oraculo only once using Streamlit's session state
    if 'oraculo_instance' not in st.session_state:
        logger.info("Criando nova instância do Oraculo para a sessão Streamlit.")
        # Show spinner *after* set_page_config
        with st.spinner("Iniciando o Oráculo... Por favor, aguarde."):
            st.session_state.oraculo_instance = Oraculo()
        logger.info("Instância do Oraculo criada e armazenada no estado da sessão.")

    oraculo = st.session_state.oraculo_instance

    # --- Rest of the Streamlit UI ---
    st.title("🔮 Oráculo Sábio")
    st.caption(f"v{__version__}")

    # Display warning if IA client failed to initialize
    if not oraculo.ia.client:
        st.warning("⚠️ O serviço de IA não pôde ser inicializado. Verifique a chave da API OpenAI e a conexão de rede. As respostas não estarão disponíveis.", icon="🚨")

    # Use st.form for better control over submission
    with st.form("pergunta_form", clear_on_submit=True):
        is_disabled = not oraculo.ia.client # Check if IA is ready
        pergunta = st.text_area("Faça sua pergunta ao oráculo:", height=100, key="pergunta_input", disabled=is_disabled)
        contexto = st.text_input("Contexto adicional (opcional):", key="contexto_input", disabled=is_disabled)
        submitted = st.form_submit_button("Consultar o Oráculo", disabled=is_disabled)

        if submitted:
            if not pergunta or not pergunta.strip():
                st.warning("Por favor, digite sua pergunta antes de consultar.")
            else:
                with st.spinner("Consultando os ventos do conhecimento..."):
                    resultado = oraculo.processar_pergunta(pergunta.strip(), contexto.strip() if contexto else None)

                # Display result or error
                if "erro" in resultado:
                    st.error(f"{resultado['erro']}")
                elif "aviso" in resultado:
                     st.warning(f"{resultado['aviso']}")
                     st.info("Sua resposta:")
                     st.markdown(resultado.get("resposta", "*O oráculo ficou em silêncio...*"))
                elif "resposta" in resultado:
                    st.markdown(f"**Resposta do Oráculo:**\n\n{resultado.get('resposta', '*O oráculo ficou em silêncio...*')}")
                else:
                    st.error("Ocorreu uma resposta inesperada do Oráculo.")


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
                    continue

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

            except EOFError:
                 print("\nEncerrado pelo usuário (EOF).")
                 break
            except KeyboardInterrupt:
                print("\nEncerrado pelo usuário (Ctrl+C).")
                break

    except Exception as e:
        logger.critical(f"Erro fatal no modo console: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"\nErro crítico encontrado: {e}")
        print("Verifique o arquivo de log para mais detalhes.")


# --- Main Execution Logic ---
if __name__ == "__main__":
    # Determine if running under Streamlit
    is_streamlit = False
    if st: # Check if streamlit was imported successfully
        try:
            # A more robust check for Streamlit execution
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx():
                is_streamlit = True
        except Exception as streamlit_check_err:
             logger.warning(f"Erro ao verificar contexto Streamlit: {streamlit_check_err}. Usando fallback.")
             # Fallback check if the above fails
             if hasattr(sys, 'argv') and 'streamlit' in sys.argv[0]:
                 is_streamlit = True

    # Execute the appropriate main function
    if is_streamlit:
         logger.info("Executando no modo Streamlit.")
         main_streamlit()
    else:
         logger.info("Executando no modo console local.")
         main_local()

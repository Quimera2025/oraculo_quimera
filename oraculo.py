import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import requests  # Fallback se notion-client falhar

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('oraculo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try imports com fallbacks
try:
    from notion_client import Client
    from openai import OpenAI
except ImportError as e:
    logger.warning(
        "Pacotes principais não encontrados. Usando fallback HTTP. "
        "Instale com: pip install notion-client openai"
    )
    HAS_MAIN_DEPS = False
else:
    HAS_MAIN_DEPS = True

# Classe de fallback para Notion API
class NotionHTTPClient:
    def __init__(self, token: str):
        self.base_url = "https://api.notion.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        })

    def query_database(self, database_id: str, filter: Optional[Dict] = None) -> Dict:
        try:
            url = f"{self.base_url}/databases/{database_id}/query"
            response = self.session.post(url, json={"filter": filter} if filter else {})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na API do Notion: {str(e)}")
            raise

    def update_page(self, page_id: str, properties: Dict) -> bool:
        try:
            url = f"{self.base_url}/pages/{page_id}"
            response = self.session.patch(url, json={"properties": properties})
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao atualizar página: {str(e)}")
            return False

class OraculoNotion:
    def __init__(self):
        self._load_config()
        self._init_clients()
        self.historico = []

    def _load_config(self):
        """Carrega configurações de variáveis de ambiente"""
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.notion_db_id = os.getenv("NOTION_DATABASE_ID")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        if not all([self.notion_token, self.notion_db_id, self.openai_key]):
            logger.error("Variáveis de ambiente faltando!")
            raise ValueError("Configurações incompletas")

    def _init_clients(self):
        """Inicializa clients com fallback"""
        try:
            if HAS_MAIN_DEPS:
                self.notion = Client(auth=self.notion_token)
                self.openai = OpenAI(api_key=self.openai_key)
            else:
                self.notion = NotionHTTPClient(self.notion_token)
                self.openai = None  # Será inicializado quando necessário
        except Exception as e:
            logger.critical(f"Falha ao iniciar clients: {str(e)}")
            raise

    def _get_openai_response(self, prompt: str) -> str:
        """Gera resposta da OpenAI com tratamento de erros"""
        try:
            if not HAS_MAIN_DEPS:
                # Fallback usando requests diretamente
                headers = {
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Você é um oráculo sábio."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 256
                }
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            
            # Uso normal do client OpenAI
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um oráculo sábio."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=256
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {str(e)}")
            return "🔮 O oráculo está temporariamente indisponível."

    def buscar_perguntas(self, horas: int = 24) -> list:
        """Busca perguntas recentes no Notion com tratamento de erros"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=horas)
            
            if HAS_MAIN_DEPS:
                resultados = self.notion.databases.query(
                    database_id=self.notion_db_id,
                    filter={
                        "property": "Criado",
                        "date": {"after": cutoff_time.isoformat()}
                    },
                    sorts=[{
                        "property": "Criado",
                        "direction": "descending"
                    }]
                )
                return resultados.get("results", [])
            
            # Fallback HTTP
            filter_data = {
                "filter": {
                    "property": "Criado",
                    "date": {"after": cutoff_time.isoformat()}
                },
                "sorts": [{
                    "property": "Criado",
                    "direction": "descending"
                }]
            }
            resultados = self.notion.query_database(self.notion_db_id, filter_data)
            return resultados.get("results", [])
            
        except Exception as e:
            logger.error(f"Erro ao buscar perguntas: {str(e)}")
            return []

    def processar_pergunta(self, item: Dict) -> bool:
        """Processa uma única pergunta e atualiza o Notion"""
        try:
            propriedades = item.get("properties", {})
            status = propriedades.get("Status", {}).get("select", {}).get("name")
            
            if status == "Respondido":
                return False

            pergunta = ""
            # Extrai pergunta de diferentes formatos do Notion
            if "Pergunta" in propriedades:
                title = propriedades["Pergunta"].get("title", [])
                if title:
                    pergunta = title[0].get("text", {}).get("content", "")

            if not pergunta:
                logger.warning("Pergunta vazia ou mal formatada")
                return False

            logger.info(f"Processando: {pergunta[:50]}...")
            
            prompt = f"""
            Como um oráculo sábio, responda com sabedoria e concisão:
            Pergunta: {pergunta}
            
            Inclua:
            - Um insight único
            - Conselho prático
            - Máximo 3 parágrafos
            """
            
            resposta = self._get_openai_response(prompt)
            
            # Prepara dados para atualização
            update_data = {
                "Resposta": {
                    "rich_text": [{"text": {"content": resposta}}]
                },
                "Status": {
                    "select": {"name": "Respondido"}
                },
                "Respondido em": {
                    "date": {"start": datetime.now().isoformat()}
                }
            }
            
            # Atualiza no Notion
            if HAS_MAIN_DEPS:
                self.notion.pages.update(
                    page_id=item["id"],
                    properties=update_data
                )
            else:
                self.notion.update_page(item["id"], update_data)
            
            logger.info("Pergunta respondida com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {str(e)}")
            return False

    def executar(self):
        """Fluxo principal com tratamento de erros global"""
        try:
            logger.info("Iniciando ciclo de processamento...")
            perguntas = self.buscar_perguntas()
            
            if not perguntas:
                logger.info("Nenhuma pergunta nova encontrada.")
                return
            
            logger.info(f"Encontradas {len(perguntas)} perguntas")
            sucessos = 0
            
            for item in perguntas:
                if self.processar_pergunta(item):
                    sucessos += 1
            
            logger.info(f"Processamento completo. {sucessos}/{len(perguntas)} respondidas")
            
        except Exception as e:
            logger.critical(f"Erro fatal no fluxo principal: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        oraculo = OraculoNotion()
        oraculo.executar()
    except Exception as e:
        logger.critical(f"Falha ao iniciar o oráculo: {str(e)}")
        exit(1)
       
     
   

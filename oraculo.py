import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# Configuração para evitar erros de encoding no Windows
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('oraculo.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

class NotionAPIClient:
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.api_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, endpoint, data=None):
        try:
            response = requests.request(
                method,
                f"{self.api_url}{endpoint}",
                headers=self.headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {method} {endpoint} - {str(e)}")
            raise

    def test_connection(self):
        """Testa se a conexão com a API está funcionando"""
        try:
            response = self._make_request("GET", "/users")
            logger.info("Conexão com Notion API estabelecida com sucesso")
            return True
        except Exception as e:
            logger.error("Falha ao conectar com Notion API")
            raise RuntimeError(f"Erro de conexão: {str(e)}")

    def get_database(self, database_id):
        """Obtém informações sobre o banco de dados"""
        return self._make_request("GET", f"/databases/{database_id}")

    def query_database(self, database_id, filter_data=None):
        """Consulta um banco de dados"""
        return self._make_request(
            "POST",
            f"/databases/{database_id}/query",
            data={"filter": filter_data} if filter_data else None
        )

    def update_page(self, page_id, properties):
        """Atualiza uma página no Notion"""
        return self._make_request(
            "PATCH",
            f"/pages/{page_id}",
            data={"properties": properties}
        )

class OpenAIHandler:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
    
    def generate_response(self, prompt):
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Você é um oráculo sábio que fornece conselhos profundos."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 256
                },
                timeout=15
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com OpenAI: {str(e)}")
            return "🔮 [O oráculo está temporariamente indisponível]"

class OraculoNotion:
    def __init__(self):
        self.notion = NotionAPIClient()
        self.openai = OpenAIHandler()
        self.db_id = os.getenv("NOTION_DATABASE_ID")
        
        # Verificação inicial
        self._verify_connection()

    def _verify_connection(self):
        """Verifica se todas as conexões estão funcionando"""
        try:
            # Testa conexão com Notion
            self.notion.test_connection()
            
            # Verifica acesso ao banco de dados
            db_info = self.notion.get_database(self.db_id)
            db_name = db_info.get("title", [{}])[0].get("text", {}).get("content", "SEM NOME")
            logger.info(f"Conectado ao banco de dados: {db_name}")
            
        except Exception as e:
            logger.critical("Falha na verificação inicial")
            logger.critical(f"1. Database ID correto? {self.db_id}")
            logger.critical(f"2. Token começa com: {self.notion.token[:8]}...")
            logger.critical("3. O banco está compartilhado com a integração?")
            raise RuntimeError(f"Verificação falhou: {str(e)}")

    def buscar_perguntas(self, horas=24):
        """Busca perguntas não respondidas nas últimas X horas"""
        try:
            cutoff_time = (datetime.now() - timedelta(hours=horas)).isoformat()
            
            resultados = self.notion.query_database(
                database_id=self.db_id,
                filter_data={
                    "and": [
                        {
                            "property": "Status",
                            "select": {"does_not_equal": "Respondido"}
                        },
                        {
                            "property": "Criado",
                            "date": {"after": cutoff_time}
                        }
                    ]
                }
            )
            return resultados.get("results", [])
        except Exception as e:
            logger.error(f"Erro ao buscar perguntas: {str(e)}")
            return []

    def processar_pergunta(self, item):
        """Processa uma pergunta e atualiza o Notion"""
        try:
            # Extrai a pergunta
            propriedades = item.get("properties", {})
            pergunta = propriedades.get("Pergunta", {}).get("title", [{}])[0].get("text", {}).get("content", "")
            
            if not pergunta:
                logger.warning("Pergunta vazia ou mal formatada")
                return False

            logger.info(f"Processando pergunta: {pergunta[:50]}...")

            # Gera resposta com IA
            prompt = f"""Como um oráculo sábio, responda de forma clara e útil:
            Pergunta: {pergunta}
            
            Inclua:
            - Um insight único
            - Conselho prático
            - Máximo 3 parágrafos"""
            
            resposta = self.openai.generate_response(prompt)

            # Atualiza o Notion
            self.notion.update_page(
                page_id=item["id"],
                properties={
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
            )
            logger.info("Pergunta respondida com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {str(e)}")
            return False

    def executar(self):
        """Fluxo principal de execução"""
        try:
            logger.info("Iniciando ciclo de processamento...")
            perguntas = self.buscar_perguntas()
            
            if not perguntas:
                logger.info("Nenhuma pergunta nova encontrada.")
                return
            
            logger.info(f"Encontradas {len(perguntas)} perguntas a responder")
            sucessos = sum(self.processar_pergunta(p) for p in perguntas)
            logger.info(f"Processamento completo. {sucessos}/{len(perguntas)} respondidas")
            
        except Exception as e:
            logger.critical(f"Erro no fluxo principal: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        oraculo = OraculoNotion()
        oraculo.executar()
    except Exception as e:
        logger.critical(f"Falha ao iniciar o oráculo: {str(e)}")
        sys.exit(1)

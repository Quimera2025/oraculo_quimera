import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests  # Usaremos requests como fallback

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

# Carrega variáveis do .env
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
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na API: {str(e)}")
            raise

    def query_database(self, database_id, filter_data=None):
        return self._make_request(
            "POST",
            f"/databases/{database_id}/query",
            data={"filter": filter_data} if filter_data else None
        )

    def update_page(self, page_id, properties):
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
                        {"role": "system", "content": "Você é um oráculo sábio."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 256
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Erro na OpenAI: {str(e)}")
            return "🔮 O oráculo está temporariamente indisponível."

class OraculoNotion:
    def __init__(self):
        self.notion = NotionAPIClient()
        self.openai = OpenAIHandler()
        self.db_id = os.getenv("NOTION_DATABASE_ID")
        
        # Verificação inicial
        self._verify_connection()

    def _verify_connection(self):
        """Verifica se as credenciais são válidas"""
        try:
            test_url = f"/databases/{self.db_id}"
            self.notion._make_request("GET", test_url)
            logger.info("✅ Conexão com Notion validada")
        except Exception as e:
            logger.critical("❌ Falha na conexão com Notion")
            raise RuntimeError(f"Verificação de conexão falhou: {str(e)}")

    def buscar_perguntas(self, horas=24):
        """Busca perguntas não respondidas"""
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
            pergunta = item["properties"]["Pergunta"]["title"][0]["text"]["content"]
            logger.info(f"Processando: {pergunta[:50]}...")
            
            resposta = self.openai.generate_response(
                f"Como oráculo, responda com sabedoria:\nPergunta: {pergunta}\n"
                "Inclua:\n- Um insight único\n- Conselho prático\n- Máximo 3 parágrafos"
            )
            
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
            return True
        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {str(e)}")
            return False

    def executar(self):
        """Fluxo principal"""
        try:
            logger.info("🔄 Iniciando ciclo de processamento...")
            perguntas = self.buscar_perguntas()
            
            if not perguntas:
                logger.info("✅ Nenhuma pergunta nova encontrada")
                return
            
            logger.info(f"📥 {len(perguntas)} perguntas a processar")
            sucessos = sum(self.processar_pergunta(p) for p in perguntas)
            logger.info(f"✅ {sucessos}/{len(perguntas)} respondidas com sucesso")
            
        except Exception as e:
            logger.critical(f"❌ Erro fatal: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        oraculo = OraculoNotion()
        oraculo.executar()
    except Exception as e:
        logger.critical(f"⛔ Falha ao iniciar o oráculo: {str(e)}")
        exit(1)

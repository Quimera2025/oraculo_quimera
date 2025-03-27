import os
from notion_client import Client
from openai import OpenAI
from datetime import datetime, timedelta

# Configurações iniciais
NOTION_TOKEN = "seu_token_integracao_notion"
NOTION_DATABASE_ID = "id_do_seu_banco_de_dados"
OPENAI_API_KEY = "sua_chave_openai"

# Inicializa clients
notion = Client(auth=NOTION_TOKEN)
openai = OpenAI(api_key=OPENAI_API_KEY)

class OraculoNotion:
    def __init__(self):
        self.historico = []
        
    def buscar_perguntas_recentes(self, horas=24):
        """Busca perguntas no Notion das últimas X horas"""
        cutoff_time = datetime.now() - timedelta(hours=horas)
        
        resultados = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "Criado",
                "date": {
                    "after": cutoff_time.isoformat()
                }
            },
            sorts=[{
                "property": "Criado",
                "direction": "descending"
            }]
        )
        
        return resultados.get("results", [])
    
    def gerar_resposta_ia(self, pergunta, contexto=None):
        """Usa OpenAI para gerar uma resposta inteligente"""
        prompt = f"""
        Você é um oráculo sábio que responde perguntas com sabedoria e insights profundos.
        Pergunta: {pergunta}
        {f'Contexto adicional: {contexto}' if contexto else ''}
        
        Sua resposta deve:
        - Ser clara e concisa
        - Incluir um insight único
        - Oferecer perspectiva prática
        - Ter no máximo 3 parágrafos
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um oráculo sábio e respeitado."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=256
        )
        
        return response.choices[0].message.content
    
    def adicionar_resposta_notion(self, pagina_id, resposta):
        """Adiciona a resposta ao banco de dados do Notion"""
        notion.pages.update(
            page_id=pagina_id,
            properties={
                "Resposta": {
                    "rich_text": [{
                        "text": {
                            "content": resposta
                        }
                    }]
                },
                "Status": {
                    "select": {
                        "name": "Respondido"
                    }
                },
                "Respondido em": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            }
        )
    
    def processar_novas_perguntas(self):
        """Processa perguntas não respondidas e gera respostas"""
        perguntas = self.buscar_perguntas_recentes()
        
        for item in perguntas:
            propriedades = item.get("properties", {})
            status = propriedades.get("Status", {}).get("select", {}).get("name")
            
            if status != "Respondido":
                pergunta = propriedades.get("Pergunta", {}).get("title", [{}])[0].get("text", {}).get("content", "")
                
                if pergunta:
                    print(f"Processando pergunta: {pergunta}")
                    resposta = self.gerar_resposta_ia(pergunta)
                    self.adicionar_resposta_notion(item["id"], resposta)
                    print(f"Resposta adicionada ao Notion!")
                    
    def executar_loop_continuo(self, intervalo_minutos=30):
        """Executa em loop verificando novas perguntas"""
        import time
        while True:
            print(f"\n{datetime.now()}: Verificando novas perguntas...")
            self.processar_novas_perguntas()
            time.sleep(intervalo_minutos * 60)

if __name__ == "__main__":
    oraculo = OraculoNotion()
    
    # Modo de operação (escolha um):
    
    # 1. Executar uma vez
    oraculo.processar_novas_perguntas()
    
    # 2. Executar em loop contínuo (para servidor)
    # oraculo.executar_loop_continuo(intervalo_minutos=30)

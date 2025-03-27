import os
import json
import logging
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Configuração de pastas
os.makedirs("dados", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

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

class GerenciadorSegredo:
    @staticmethod
    def carregar_chave():
        """Carrega a chave de forma segura"""
        try:
            # Em produção, use variáveis de ambiente ou um gerenciador de segredos
            return "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"
        except Exception as e:
            logger.critical(f"Erro ao carregar chave: {str(e)}")
            raise

class BancoDeDados:
    def __init__(self):
        self.arquivo = Path("dados/perguntas.json")
        self.carregar_dados()

    def carregar_dados(self):
        try:
            if not self.arquivo.exists():
                self.dados = {"perguntas": []}
                self.salvar_dados()
            else:
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    self.dados = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}")
            self.dados = {"perguntas": []}

    def salvar_dados(self):
        try:
            with open(self.arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.dados, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar dados: {str(e)}")

    def adicionar_pergunta(self, pergunta, arquivo=None):
        registro = {
            "id": len(self.dados["perguntas"]) + 1,
            "pergunta": pergunta,
            "resposta": None,
            "arquivo": arquivo,
            "data": datetime.now().isoformat(),
            "respondida": False
        }
        self.dados["perguntas"].append(registro)
        self.salvar_dados()
        return registro

    def responder_pergunta(self, id_pergunta, resposta):
        for item in self.dados["perguntas"]:
            if item["id"] == id_pergunta:
                item["resposta"] = resposta
                item["respondida"] = True
                item["data_resposta"] = datetime.now().isoformat()
                self.salvar_dados()
                return True
        return False

class GerenciadorIA:
    def __init__(self):
        self.client = OpenAI(api_key=GerenciadorSegredo.carregar_chave())

    def gerar_resposta(self, pergunta, contexto=None):
        try:
            prompt = f"""Você é um oráculo ancestral com sabedoria infinita.
            
            Pergunta: {pergunta}
            
            Contexto adicional: {contexto if contexto else "Nenhum"}
            
            Forneça:
            1. Um insight profundo
            2. Um conselho prático
            3. Uma metáfora ilustrativa
            (Máximo 3 parágrafos)"""

            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "Você é um oráculo sábio e respeitado."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=350
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {str(e)}")
            return "🔮 [O oráculo está temporariamente indisponível]"

class Oraculo:
    def __init__(self):
        self.db = BancoDeDados()
        self.ia = GerenciadorIA()

    def processar_pergunta(self, pergunta, arquivo=None):
        try:
            caminho_arquivo = None
            if arquivo:
                caminho_arquivo = self._salvar_arquivo(arquivo)
            
            registro = self.db.adicionar_pergunta(pergunta, caminho_arquivo)
            logger.info(f"Processando pergunta ID {registro['id']}")
            
            resposta = self.ia.gerar_resposta(pergunta)
            self.db.responder_pergunta(registro['id'], resposta)
            
            return registro
        except Exception as e:
            logger.error(f"Erro no processamento: {str(e)}")
            raise

    def _salvar_arquivo(self, file):
        upload_path = Path("uploads") / file.filename
        try:
            with open(upload_path, 'wb') as f:
                f.write(file.read())
            return str(upload_path)
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo: {str(e)}")
            return None

    def listar_perguntas(self, respondidas=False):
        return [p for p in self.db.dados["perguntas"] if p["respondida"] == respondidas]

# Interface simples
if __name__ == "__main__":
    print("=== ORÁCULO SÁBIO ===")
    oraculo = Oraculo()
    
    while True:
        print("\n1. Fazer pergunta")
        print("2. Ver perguntas/respostas")
        print("3. Sair")
        
        opcao = input("Escolha: ")
        
        if opcao == "1":
            pergunta = input("\nSua pergunta: ")
            arquivo = None  # Implemente upload real se necessário
            
            resultado = oraculo.processar_pergunta(pergunta, arquivo)
            print(f"\nResposta: {resultado['resposta']}")
            
        elif opcao == "2":
            print("\nHistórico completo:")
            for p in oraculo.listar_perguntas(respondidas=True):
                print(f"\nID {p['id']} - {p['data']}")
                print(f"Pergunta: {p['pergunta']}")
                print(f"Resposta: {p['resposta']}")
                if p['arquivo']:
                    print(f"Arquivo: {p['arquivo']}")
        
        elif opcao == "3":
            break

    print("Até logo, buscador da verdade!")

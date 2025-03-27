import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Configuração inicial
load_dotenv()  # Carrega variáveis do .env

# Verificação crítica das variáveis
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Chave OpenAI não encontrada no arquivo .env")

# Configuração de pastas
Path("dados").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('oraculo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BancoDeDados:
    # ... (mantenha igual ao código anterior) ...
    # Métodos: carregar_dados, salvar_dados, adicionar_pergunta, responder_pergunta

class GerenciadorIA:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.config = {
            "model": os.getenv("MODEL_IA", "gpt-4-turbo"),
            "temperature": float(os.getenv("TEMPERATURA", 0.7)),
            "max_tokens": int(os.getenv("MAX_TOKENS", 350))
        }

    def gerar_resposta(self, pergunta):
        try:
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um oráculo ancestral. Forneça insights profundos em 3 partes: 1) Verdade universal 2) Conselho prático 3) Metáfora"
                    },
                    {
                        "role": "user",
                        "content": pergunta
                    }
                ],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro na IA: {str(e)}")
            return "🔮 [O oráculo está em silêncio hoje]"

class Oraculo:
    # ... (mantenha a mesma estrutura da versão anterior) ...
    # Métodos: processar_pergunta, _salvar_arquivo, listar_perguntas

# Interface de linha de comando
if __name__ == "__main__":
    try:
        print("\n=== ORÁCULO SÁBIO ===")
        print(f"Modelo: {os.getenv('MODEL_IA')}")
        print("----------------------")
        
        oraculo = Oraculo()
        
        while True:
            print("\n1. Fazer pergunta\n2. Ver histórico\n3. Sair")
            opcao = input("Escolha: ").strip()
            
            if opcao == "1":
                pergunta = input("\nSua pergunta: ").strip()
                if pergunta:
                    resultado = oraculo.processar_pergunta(pergunta)
                    print(f"\n💡 Resposta:\n{resultado['resposta']}")
                else:
                    print("Por favor, digite uma pergunta válida.")
            
            elif opcao == "2":
                print("\n📜 Histórico:")
                for p in oraculo.listar_perguntas(respondidas=True):
                    print(f"\nID {p['id']} - {p['data']}")
                    print(f"Pergunta: {p['pergunta']}")
                    print(f"Resposta: {p['resposta']}")
            
            elif opcao == "3":
                print("\nAté a próxima busca por sabedoria!")
                break
            
            else:
                print("Opção inválida. Tente 1, 2 ou 3.")
    
    except Exception as e:
        logger.critical(f"Falha crítica: {str(e)}")
        print("O oráculo encontrou um erro. Verifique os logs.")

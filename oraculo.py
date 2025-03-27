#!/usr/bin/env python3
"""
Módulo Oráculo - Sistema de perguntas e respostas com integração OpenAI
"""

__version__ = "0.2.0"
__author__ = "Seu Nome"
__license__ = "MIT"

import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Union
from dotenv import load_dotenv
from openai import OpenAI

# Configuração inicial
load_dotenv()

# Verificação das variáveis de ambiente
if not os.getenv("OPENAI_API_KEY"):
    print("AVISO: Chave OpenAI não encontrada no arquivo .env")
    print("Crie um arquivo .env com OPENAI_API_KEY=sua_chave_aqui")

# Configuração de pastas
UPLOAD_FOLDER = Path("uploads")
DATA_FOLDER = Path("dados")

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

class ArquivoHandler:
    """Classe para manipulação de arquivos enviados"""
    
    @staticmethod
    def validar_arquivo(nome_arquivo: str) -> bool:
        """Valida se o arquivo tem extensão permitida"""
        extensoes_permitidas = {'.pdf', '.docx', '.txt'}
        return Path(nome_arquivo).suffix.lower() in extensoes_permitidas
    
    @staticmethod
    def salvar_arquivo(arquivo) -> Optional[str]:
        """Salva arquivo no sistema e retorna o caminho"""
        if arquivo and hasattr(arquivo, 'filename'):
            if ArquivoHandler.validar_arquivo(arquivo.filename):
                caminho = UPLOAD_FOLDER / Path(arquivo.filename).name
                arquivo.save(caminho)
                return str(caminho)
        return None
    
    @staticmethod
    def extrair_texto(caminho_arquivo: str) -> str:
        """Extrai texto de arquivos PDF/DOCX/TXT"""
        try:
            from PyPDF2 import PdfReader
            import docx
            
            caminho = Path(caminho_arquivo)
            if caminho.suffix == '.pdf':
                with open(caminho, 'rb') as f:
                    leitor = PdfReader(f)
                    texto = ' '.join([pagina.extract_text() for pagina in leitor.pages])
            elif caminho.suffix == '.docx':
                doc = docx.Document(caminho)
                texto = '\n'.join([paragrafo.text for paragrafo in doc.paragraphs])
            else:  # TXT
                with open(caminho, 'r', encoding='utf-8') as f:
                    texto = f.read()
            
            # Limpa texto removendo múltiplos espaços/quebras de linha
            return re.sub(r'\s+', ' ', texto).strip()
        except Exception as e:
            logger.error(f"Erro ao extrair texto: {str(e)}")
            return ""

class BancoDeDados:
    def __init__(self):
        self.arquivo = DATA_FOLDER / "perguntas.json"
        self.carregar_dados()

    def carregar_dados(self) -> None:
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

    def salvar_dados(self) -> None:
        try:
            with open(self.arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.dados, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar dados: {str(e)}")

    def adicionar_pergunta(self, pergunta: str, arquivo: Optional[str] = None) -> Dict:
        registro = {
            "id": len(self.dados["perguntas"]) + 1,
            "pergunta": pergunta,
            "resposta": None,
            "arquivo": arquivo,
            "texto_arquivo": ArquivoHandler.extrair_texto(arquivo) if arquivo else None,
            "data": datetime.now().isoformat(),
            "respondida": False
        }
        self.dados["perguntas"].append(registro)
        self.salvar_dados()
        return registro

    def responder_pergunta(self, id_pergunta: int, resposta: str) -> bool:
        for item in self.dados["perguntas"]:
            if item["id"] == id_pergunta:
                item["resposta"] = resposta
                item["respondida"] = True
                item["data_resposta"] = datetime.now().isoformat()
                self.salvar_dados()
                return True
        return False

    def listar_perguntas(self, respondidas: Optional[bool] = None) -> List[Dict]:
        """Filtra perguntas por status de resposta"""
        if respondidas is None:
            return self.dados["perguntas"]
        return [p for p in self.dados["perguntas"] if p["respondida"] == respondidas]

class GerenciadorIA:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

    def gerar_resposta(self, pergunta: str, contexto: Optional[str] = None) -> str:
        if not self.client:
            return "⚠️ Erro: Chave OpenAI não configurada. Crie um arquivo .env com OPENAI_API_KEY"

        try:
            prompt = [
                {"role": "system", "content": "Você é um oráculo sábio que fornece conselhos úteis."},
                {"role": "user", "content": pergunta}
            ]
            
            if contexto:
                prompt.insert(1, {"role": "system", "content": f"Contexto do documento: {contexto}"})

            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_IA", "gpt-3.5-turbo"),
                messages=prompt,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {str(e)}")
            return "🔮 O oráculo está temporariamente indisponível"

class Oraculo:
    def __init__(self):
        self.db = BancoDeDados()
        self.ia = GerenciadorIA()

    def processar_pergunta(self, pergunta: str, arquivo=None) -> Dict:
        caminho_arquivo = ArquivoHandler.salvar_arquivo(arquivo) if arquivo else None
        registro = self.db.adicionar_pergunta(pergunta, caminho_arquivo)
        
        contexto = registro.get("texto_arquivo", "")
        resposta = self.ia.gerar_resposta(pergunta, contexto)
        
        self.db.responder_pergunta(registro["id"], resposta)
        return registro

    def historico(self, limit: int = 5) -> List[Dict]:
        """Mostra as últimas perguntas/respostas"""
        return sorted(self.db.dados["perguntas"], 
                     key=lambda x: x["data"], 
                     reverse=True)[:limit]

def main():
    print(f"=== ORÁCULO SÁBIO (v{__version__}) ===")
    print("(Digite 'sair' para encerrar, 'historico' para ver últimas perguntas)\n")
    
    oraculo = Oraculo()
    
    try:
        while True:
            entrada = input("Faça sua pergunta: ").strip()
            
            if entrada.lower() == 'sair':
                print("\nAté a próxima busca por sabedoria!")
                break
                
            if entrada.lower() == 'historico':
                print("\nÚltimas perguntas:")
                for item in oraculo.historico():
                    print(f"\n[{item['data']}] Q: {item['pergunta']}")
                    if item['respondida']:
                        print(f"A: {item['resposta']}")
                print()
                continue
                
            if not entrada:
                print("Por favor, digite uma pergunta válida.")
                continue
                
            resultado = oraculo.processar_pergunta(entrada)
            print(f"\nResposta: {resultado['resposta']}\n")
            
    except KeyboardInterrupt:
        print("\n\nEncerrado pelo usuário")
    except Exception as e:
        logger.critical(f"Erro fatal: {str(e)}")
        print("O oráculo encontrou um erro crítico. Verifique o arquivo oraculo.log")

if __name__ == "__main__":
    main()

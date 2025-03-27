import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Configuração básica
load_dotenv()

# Estrutura de diretórios
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/oraculo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LocalDatabase:
    """Armazenamento local em JSON"""
    def __init__(self):
        self.file = Path("data/perguntas.json")
        self.data = self._load_data()

    def _load_data(self):
        try:
            if self.file.exists():
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"perguntas": []}
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return {"perguntas": []}

    def save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def add_question(self, question):
        new_id = len(self.data["perguntas"]) + 1
        self.data["perguntas"].append({
            "id": new_id,
            "question": question,
            "answer": None,
            "timestamp": datetime.now().isoformat()
        })
        self.save()
        return new_id

    def add_answer(self, question_id, answer):
        for q in self.data["perguntas"]:
            if q["id"] == question_id:
                q["answer"] = answer
                q["answered_at"] = datetime.now().isoformat()
                self.save()
                return True
        return False

class OracleEngine:
    """Motor de respostas com fallback local"""
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.local_responses = [
            "A sabedoria vem de dentro",
            "Reveja seus pressupostos",
            "Tudo tem seu tempo",
            "A resposta está na pergunta"
        ]

    def generate_response(self, question):
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return self._get_fallback_response()
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=os.getenv("MODEL", "gpt-3.5-turbo"),
                messages=[{
                    "role": "system",
                    "content": "Você é um oráculo. Responda de forma concisa e sábia."
                }, {
                    "role": "user", 
                    "content": question
                }],
                max_tokens=150
            )
            return response.choices[0].message.content
        except ImportError:
            return self._get_fallback_response()
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            return self._get_fallback_response()

    def _get_fallback_response(self):
        from random import choice
        return choice(self.local_responses)

def main():
    print("\n🔮 Oráculo Python - Modo Seguro para GitHub\n")
    print("(Digite 'sair' para encerrar)\n")
    
    db = LocalDatabase()
    oracle = OracleEngine()
    
    try:
        while True:
            question = input("Sua pergunta: ").strip()
            
            if question.lower() in ('sair', 'exit', 'quit'):
                break
                
            if not question:
                print("Por favor, faça uma pergunta válida.")
                continue
                
            q_id = db.add_question(question)
            answer = oracle.generate_response(question)
            db.add_answer(q_id, answer)
            
            print(f"\nResposta: {answer}\n")
            
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        print("\nVolte quando precisar de sabedoria!")

if __name__ == "__main__":
    main()

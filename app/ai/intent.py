import json
from .ollama_client import ollama

SYSTEM = """You are a medical AI assistant. Analyze the request and reply ONLY with valid JSON.

Tables: patients, consultations, medical_records, ai_diagnosis, appointments,
        medical_staff, services, ai_chat_history, audit_logs, notifications

Required JSON format (nothing else, no surrounding text):
{
  "intent": "SELECT" | "INSERT" | "UPDATE" | "QUESTION",
  "table": "table_name" | null,
  "attributes": {"column": "value"},
  "missing_fields": ["field1"],
  "needs_clarification": true | false,
  "clarification_question": "Question to ask" | null,
  "confidence": 0.0..1.0
}

Required fields per table:
- patients: first_name, last_name, birthdate
- consultations: id_patient, symptoms
- appointments: id_patient, appointment_date"""

class IntentDetector:
    def detect(self, query, history=[]):
        context = ""
        if history:
            for m in history[-4:]:
                r = "User" if m['role']=='user' else "System"
                context += f"{r}: {m['content']}\n"
        prompt = (f"Context:\n{context}\n" if context else "") + f"Request: {query}"

        raw = ollama.generate('llama3.2:3b', prompt, system=SYSTEM, temperature=0.1)

        try:
            clean = raw.strip()
            if '```' in clean:
                parts = clean.split('```')
                clean = parts[1].lstrip('json').strip() if len(parts)>1 else parts[0]
            return json.loads(clean)
        except:
            return {"intent":"QUESTION","table":None,"attributes":{},
                    "missing_fields":[],"needs_clarification":True,
                    "clarification_question":"Could you please rephrase your request?",
                    "confidence":0.0}

intent_detector = IntentDetector()
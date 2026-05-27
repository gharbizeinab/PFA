import json
from .ollama_client import ollama

SYSTEM = """Tu es un assistant IA médical. Analyse la requête et réponds UNIQUEMENT en JSON valide.

Tables : patients, consultations, medical_records, ai_diagnosis, appointments,
         medical_staff, services, ai_chat_history, audit_logs, notifications

Format JSON obligatoire (rien d'autre, pas de texte) :
{
  "intent": "SELECT" | "INSERT" | "UPDATE" | "QUESTION",
  "table": "nom_table" | null,
  "attributes": {"colonne": "valeur"},
  "missing_fields": ["champ1"],
  "needs_clarification": true | false,
  "clarification_question": "Question à poser" | null,
  "confidence": 0.0..1.0
}

Champs obligatoires :
- patients: first_name, last_name, birthdate
- consultations: id_patient, symptoms
- appointments: id_patient, appointment_date"""

class IntentDetector:
    def detect(self, query, history=[]):
        context = ""
        if history:
            for m in history[-4:]:
                r = "Utilisateur" if m['role']=='user' else "Système"
                context += f"{r}: {m['content']}\n"
        prompt = (f"Contexte:\n{context}\n" if context else "") + f"Requête: {query}"

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
                    "clarification_question":"Pouvez-vous reformuler votre demande ?",
                    "confidence":0.0}

intent_detector = IntentDetector()
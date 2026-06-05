import json
from .ollama_client import ollama

TABLE_SCHEMA = {
    "patients":        ["first_name", "last_name", "birthdate", "age", "gender", "blood_group"],
    "consultations":   ["id_patient", "consultation_date", "status", "diagnosis", "symptoms"],
    "medical_records": ["id_patient", "allergies", "chronic_diseases", "blood_group", "height", "weight"],
    "ai_diagnosis":    ["id_consultation", "predicted_disease", "confidence_score"],
    "appointments":    ["id_patient", "id_staff", "appointment_date", "reason", "status"],
    "medical_staff":   ["id_user", "id_service", "name_staff", "speciality"],
    "services":        ["service_name"],
    "notifications":   ["message", "type"],
    "users":           ["email", "role"],
    "medical_documents": ["id_patient", "file_type", "file_path"],
    "audit_logs":      [],
    "ai_chat_history": [],
}

# Appel 1 — colonnes et filtres uniquement
SYSTEM_COLUMNS = """Tu es un extracteur d'informations médicales précis.
Ta seule tâche : extraire les colonnes et filtres mentionnés dans la phrase.

RÈGLES :
- Réponds UNIQUEMENT en JSON valide, aucun texte autour
- Pour SELECT avec filtre : {"colonne": "valeur_complete"}
- Pour SELECT sans filtre sur une colonne spécifique : {"colonne": null}
- Pour INSERT/UPDATE : {"colonne": "valeur extraite"}
- Les dates au format ISO : YYYY-MM-DD
- Si rien n'est extractible, réponds : {}

EXEMPLES :
Phrase: "Find all female patients"         → {"gender": "female"}
Phrase: "Find all male patients"           → {"gender": "male"}
Phrase: "Show patients older than 70"      → {"age": 70}
Phrase: "Show patients younger than 50"    → {"age": 50}
Phrase: "Show first and last names"        → {"first_name": null, "last_name": null}
Phrase: "Find patient named John Doe"      → {"first_name": "John", "last_name": "Doe"}
Phrase: "List all patients"                → {}"""

# Appel 2 — agrégat uniquement
SYSTEM_AGGREGATE = """Tu es un détecteur d'agrégat SQL.
Ta seule tâche : détecter si la phrase demande un calcul mathématique.

RÈGLES :
- Réponds UNIQUEMENT en JSON valide, aucun texte autour
- Si la question demande une quantité ou dénombrement → {"aggregate": "COUNT(*)"}
- Si la question demande une moyenne                  → {"aggregate": "AVG(age)"}
- Si la question demande la valeur maximale           → {"aggregate": "MAX(age)"}
- Si la question demande la valeur minimale           → {"aggregate": "MIN(age)"}
- Si aucun calcul demandé                             → {}

EXEMPLES :
Phrase: "Count total number of patients"   → {"aggregate": "COUNT(*)"}
Phrase: "How many patients are there"      → {"aggregate": "COUNT(*)"}
Phrase: "Show average patient age"         → {"aggregate": "AVG(age)"}
Phrase: "Find the oldest patient"          → {"aggregate": "MAX(age)"}
Phrase: "Find the youngest patient"        → {"aggregate": "MIN(age)"}
Phrase: "List all patients"                → {}"""

# Appel 3 — tri, groupe, jointure uniquement
SYSTEM_SORT = """Tu es un détecteur de tri et regroupement SQL.
Ta seule tâche : détecter si la phrase demande un tri, regroupement ou jointure.

RÈGLES :
- Réponds UNIQUEMENT en JSON valide, aucun texte autour
- Si la question demande un tri                  → {"order_by": "colonne ASC ou DESC"}
- Si la question demande un regroupement         → {"group_by": "colonne"}
- Si la question combine deux tables             → {"join": "nom_table"}
- Si rien de tout ça                             → {}

EXEMPLES :
Phrase: "Show patients sorted by age descending"        → {"order_by": "age DESC"}
Phrase: "Show staff sorted alphabetically"              → {"order_by": "name_staff ASC"}
Phrase: "Show average age by gender"                    → {"group_by": "gender"}
Phrase: "Count patients by blood group"                 → {"group_by": "blood_group"}
Phrase: "Show all consultations with patient names"     → {"join": "patients"}
Phrase: "List all patients"                             → {}"""


def _parse(raw: str) -> dict:
    try:
        clean = raw.strip()
        if '```' in clean:
            parts = clean.split('```')
            clean = parts[1].lstrip('json').strip() if len(parts) > 1 else parts[0]
        result = json.loads(clean)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


class AttributeExtractor:
    def extract(self, query: str, table: str, intent: str) -> dict:
        columns = TABLE_SCHEMA.get(table, [])
        if not columns:
            return {}

        # Appel 1 — colonnes + filtres
        raw1 = ollama.generate('llama3.2:3b',
            f"Table: {table}\nColonnes disponibles: {', '.join(columns)}\nAction: {intent}\nPhrase: {query}\n\nJSON:",
            system=SYSTEM_COLUMNS, temperature=0.1)
        result1 = {k: v for k, v in _parse(raw1).items() if k in columns}

        # Appel 2 — agrégat
        raw2 = ollama.generate('llama3.2:3b',
            f"Colonnes disponibles: {', '.join(columns)}\nPhrase: {query}\n\nJSON:",
            system=SYSTEM_AGGREGATE, temperature=0.1)
        result2 = {k: v for k, v in _parse(raw2).items() if k == "aggregate"}

        # Appel 3 — tri / groupe / jointure
        raw3 = ollama.generate('llama3.2:3b',
            f"Table: {table}\nColonnes disponibles: {', '.join(columns)}\nPhrase: {query}\n\nJSON:",
            system=SYSTEM_SORT, temperature=0.1)
        result3 = {k: v for k, v in _parse(raw3).items() if k in {"order_by", "group_by", "join"}}

        return {**result1, **result2, **result3}


attribute_extractor = AttributeExtractor()

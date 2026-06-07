import json
from .ollama_client import ollama

TABLE_SCHEMA = {
    "patients":        ["first_name", "last_name", "birthdate", "age", "gender", "blood_group"],
    "consultations":   ["id_patient", "consultation_date", "status", "diagnosis", "symptoms", "name_staff"],
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

SYSTEM_COMBINED = """You are a precise medical SQL attribute extractor.
Analyze the sentence and return ONLY this JSON structure, nothing else:
{
  "columns": {},
  "aggregate": {},
  "sort": {}
}

RULES for "columns":
- Column with filter: {"column": "value"}
- Column requested without filter: {"column": null}
- Dates in ISO format: YYYY-MM-DD
- Only use columns from the available list

RULES for "aggregate":
- Count/quantity  → {"aggregate": "COUNT(*)"}
- Average         → {"aggregate": "AVG(col)"}
- Maximum         → {"aggregate": "MAX(col)"}
- Minimum         → {"aggregate": "MIN(col)"}
- No calc needed  → {}

RULES for "sort":
- Sorting    → {"order_by": "col ASC|DESC"}
- Grouping   → {"group_by": "col"}
- Join       → {"join": "table_name"}
- Nothing    → {}

EXAMPLES:
"Patients with blood type A+"
→ {"columns": {"blood_group": "A+"}, "aggregate": {}, "sort": {}}

"Show patient ID and birthdate"
→ {"columns": {"id_patient": null, "birthdate": null}, "aggregate": {}, "sort": {}}

"How many consultations exist"
→ {"columns": {}, "aggregate": {"aggregate": "COUNT(*)"}, "sort": {}}

"Average weight per blood type"
→ {"columns": {}, "aggregate": {"aggregate": "AVG(weight)"}, "sort": {"group_by": "blood_group"}}

"Sort appointments by date ascending"
→ {"columns": {}, "aggregate": {}, "sort": {"order_by": "appointment_date ASC"}}

"Show diagnoses with patient full name"
→ {"columns": {}, "aggregate": {}, "sort": {"join": "patients"}}

"Show consultations with patient names"
→ {"columns": {}, "aggregate": {}, "sort": {"join": "patients"}}

"List all records"
→ {"columns": {}, "aggregate": {}, "sort": {}}

"List all staff"
→ {"columns": {}, "aggregate": {}, "sort": {}}

"Show patients older than 70"
→ {"columns": {"age": ">70"}, "aggregate": {}, "sort": {}}

"Show patients younger than 50"
→ {"columns": {"age": "<50"}, "aggregate": {}, "sort": {}}

"Show patients above 60 years old"
→ {"columns": {"age": ">60"}, "aggregate": {}, "sort": {}}

"Find the oldest patient"
→ {"columns": {}, "aggregate": {"aggregate": "MAX(age)"}, "sort": {}}

"Find the youngest patient"
→ {"columns": {}, "aggregate": {"aggregate": "MIN(age)"}, "sort": {}}

"Show staff sorted alphabetically"
→ {"columns": {}, "aggregate": {}, "sort": {"order_by": "name_staff ASC"}}

"Count patients by blood group"
→ {"columns": {}, "aggregate": {"aggregate": "COUNT(*)"}, "sort": {"group_by": "blood_group"}}

"Count consultations by status"
→ {"columns": {}, "aggregate": {"aggregate": "COUNT(*)"}, "sort": {"group_by": "status"}}

"Show average age by gender"
→ {"columns": {}, "aggregate": {"aggregate": "AVG(age)"}, "sort": {"group_by": "gender"}}

"Show today's consultations for Dr. Ali"
→ {"columns": {"name_staff": "Dr. Ali", "consultation_date": "today"}, "aggregate": {}, "sort": {}}

"List consultations of Dr. Ines Hammami today"
→ {"columns": {"name_staff": "Dr. Ines Hammami", "consultation_date": "today"}, "aggregate": {}, "sort": {}}

"Show consultations of Dr. Khelifi"
→ {"columns": {"name_staff": "Dr. Khelifi"}, "aggregate": {}, "sort": {}}"""


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

        raw = ollama.chat(
            'llama3.2:3b',
            f"Table: {table}\nAvailable columns: {', '.join(columns)}\nAction: {intent}\nSentence: {query}\n\nJSON:",
            system=SYSTEM_COMBINED,
            temperature=0.1,
            top_p=0.9,
            num_predict=256,
        )
        parsed = _parse(raw)

        result = {}

        cols = parsed.get("columns", {})
        if isinstance(cols, dict):
            result.update({k: v for k, v in cols.items() if k in columns})

        agg = parsed.get("aggregate", {})
        if isinstance(agg, dict) and "aggregate" in agg:
            result["aggregate"] = agg["aggregate"]

        srt = parsed.get("sort", {})
        if isinstance(srt, dict):
            result.update({k: v for k, v in srt.items() if k in {"order_by", "group_by", "join"}})

        return result


attribute_extractor = AttributeExtractor()

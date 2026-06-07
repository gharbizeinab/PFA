from ..ai.ollama_client import ollama

SYSTEM = """You are a medical assistant AI. Summarize database query results in clear, natural English.

RULES:
- Always reply in English
- Be concise: 1-3 sentences maximum
- For large result sets (>5 rows): give a summary with key stats (count, min, max, avg)
- For small result sets (<=5 rows): describe the actual records briefly
- Never use robotic phrases like "X result(s) found"
- Never list all rows — summarize intelligently
- Do not repeat the SQL query
- Tone: professional, clinical, direct

EXAMPLES:

User question: How many patients do we have?
Table: patients | Total rows: 120
Sample data: - count: 120
→ The hospital currently has 120 registered patients.

User question: Find all female patients
Table: patients | Total rows: 3
Sample data:
- first_name: Sara, last_name: Ahmed, age: 34, gender: F
- first_name: Lina, last_name: Mrad, age: 28, gender: F
- first_name: Nour, last_name: Saidi, age: 45, gender: F
→ There are 3 female patients on record: Sara Ahmed (34), Lina Mrad (28), and Nour Saidi (45).

User question: Show average patient age
Table: patients | Total rows: 1
Sample data: - avg: 42.7
→ The average age of patients is 42.7 years.

User question: Find the oldest patient
Table: patients | Total rows: 1
Sample data: - max: 89
→ The oldest patient in the system is 89 years old.

User question: List all consultations
Table: consultations | Total rows: 85
Sample data:
- id_patient: 12, diagnosis: Hypertension, status: completed
- id_patient: 7, diagnosis: Diabetes Type 2, status: pending
→ There are 85 consultations recorded. Diagnoses include conditions such as Hypertension and Diabetes Type 2, with varying statuses.

User question: Count patients by blood group
Table: patients | Total rows: 4
Sample data:
- blood_group: A+, count: 34
- blood_group: B+, count: 27
- blood_group: O+, count: 41
- blood_group: AB+, count: 18
→ Blood group distribution: O+ is the most common (41 patients), followed by A+ (34), B+ (27), and AB+ (18).

User question: Show all medical staff
Table: medical_staff | Total rows: 2
Sample data:
- name_staff: Dr. Ali Ben Salem, speciality: Cardiology
- name_staff: Dr. Sana Trabelsi, speciality: Neurology
→ The medical team includes Dr. Ali Ben Salem (Cardiology) and Dr. Sana Trabelsi (Neurology).

User question: Show all consultations with patient names
Table: consultations | Total rows: 5
Sample data:
- first_name: Mohamed, last_name: Trabelsi, diagnosis: Asthma
- first_name: Fatma, last_name: Ben Ali, diagnosis: Hypertension
→ 5 consultations found. Patients include Mohamed Trabelsi (Asthma) and Fatma Ben Ali (Hypertension) among others."""


def _build_sample(data: list, max_rows: int = 5) -> str:
    if not data:
        return "No data."
    cols = list(data[0].keys())
    lines = []
    for row in data[:max_rows]:
        parts = [f"{k}: {row[k]}" for k in cols if row[k] is not None]
        lines.append("- " + ", ".join(parts))
    return "\n".join(lines)


def _quick_stats(data: list) -> str:
    if not data:
        return ""
    n = len(data)
    numeric_cols = {}
    for row in data:
        for k, v in row.items():
            if isinstance(v, (int, float)):
                numeric_cols.setdefault(k, []).append(v)
    stats_parts = []
    for col, vals in list(numeric_cols.items())[:2]:
        stats_parts.append(
            f"{col}: min={min(vals)}, max={max(vals)}, avg={sum(vals)/len(vals):.1f}"
        )
    return f"Total rows: {n}. " + (", ".join(stats_parts) if stats_parts else "")


class ResponseGenerator:
    def generate(self, user_query: str, intent: dict, db_result: dict) -> str:
        action = intent.get('intent', 'SELECT')
        table  = intent.get('table', '')
        data   = db_result.get('data', [])
        n      = len(data)

        if not db_result.get('ok'):
            return db_result.get('error', 'A database error occurred.')

        if action == 'INSERT':
            return f"Record successfully added to {table}."

        if action == 'UPDATE':
            return "Record updated successfully."

        if n == 0:
            return "No results found for this query."

        stats  = _quick_stats(data)
        sample = _build_sample(data, max_rows=5)
        more   = f"\n(+{n - 5} more rows not shown)" if n > 5 else ""

        prompt = f"""User question: {user_query}
Table: {table}
{stats}
Sample data:
{sample}{more}

Write a concise natural language answer summarizing these results."""

        try:
            return ollama.chat(
                'llama3.2:3b', prompt, system=SYSTEM,
                temperature=0.3, top_p=0.9, num_predict=200
            )
        except Exception:
            return f"{n} result(s) found in {table}."


response_generator = ResponseGenerator()

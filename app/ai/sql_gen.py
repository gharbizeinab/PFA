from .ollama_client import ollama

SQL_SYSTEM = """Expert SQL PostgreSQL médical. Génère UNIQUEMENT du SQL valide, rien d'autre.

RÈGLES ABSOLUES :
- Autorisé : SELECT, INSERT, UPDATE uniquement
- INTERDIT : DROP, TRUNCATE, ALTER, DELETE, GRANT, EXEC
- Pour supprimer : UPDATE table SET is_deleted=TRUE WHERE id=:id
- Utilise TOUJOURS des paramètres liés : :nom, :prenom (jamais de valeurs directes)
- La colonne AGE existe directement dans patients (INTEGER), n'utilise JAMAIS birthdate pour calculer l'âge
- Termine par un point-virgule

TABLES :
patients(id_patient, id_user, first_name, last_name, birthdate, gender, age INTEGER, blood_group)
consultations(id_consultation, id_staff, id_patient, consultation_date, status, diagnosis, symptoms)
medical_records(id_record, id_patient, allergies, chronic_diseases, blood_group, height, weight)
ai_diagnosis(id_ai_diagnosis, id_consultation, predicted_disease, confidence_score)
appointments(id_appointment, id_patient, id_staff, appointment_date, reason, status)
medical_staff(id_staff, id_user, id_service, name_staff, speciality)
services(id_service, service_name)

EXEMPLES :

Action: SELECT | Table: patients | Colonnes: toutes | Filtres: aucun
→ SELECT * FROM patients;

Action: SELECT | Table: patients | Colonnes: [first_name, last_name] | Filtres: aucun
→ SELECT first_name, last_name FROM patients;

Action: SELECT | Table: patients | Colonnes: COUNT(*) | Filtres: aucun
→ SELECT COUNT(*) FROM patients;

Action: SELECT | Table: patients | Colonnes: COUNT(*) | Filtres: {gender: :gender}
→ SELECT COUNT(*) FROM patients WHERE gender = :gender;

Action: SELECT | Table: patients | Colonnes: toutes | Filtres: {gender: :gender}
→ SELECT * FROM patients WHERE gender = :gender;

Action: SELECT | Table: patients | Colonnes: AVG(age) | Filtres: aucun
→ SELECT AVG(age) FROM patients;

Action: SELECT | Table: patients | Colonnes: [first_name, last_name, age] | Filtres: {age: >70}
→ SELECT first_name, last_name, age FROM patients WHERE age > 70;

Action: SELECT | Table: patients | Colonnes: [first_name, last_name, age] | ORDER BY: age DESC
→ SELECT first_name, last_name, age FROM patients ORDER BY age DESC;

Action: SELECT | Table: patients | Colonnes: [blood_group, COUNT(*)] | GROUP BY: blood_group
→ SELECT blood_group, COUNT(*) FROM patients GROUP BY blood_group;

Action: SELECT | Table: consultations | JOIN: patients ON id_patient | Colonnes: [first_name, last_name, diagnosis]
→ SELECT p.first_name, p.last_name, c.diagnosis FROM consultations c JOIN patients p ON c.id_patient = p.id_patient;

Action: INSERT | Table: patients | Valeurs: {first_name: :first_name, last_name: :last_name, age: :age, id_user: :id_user}
→ INSERT INTO patients (id_user, first_name, last_name, age) VALUES (:id_user, :first_name, :last_name, :age);

Action: UPDATE | Table: patients | SET: {age: :age} | Filtres: {first_name: :first_name, last_name: :last_name}
→ UPDATE patients SET age = :age WHERE first_name = :first_name AND last_name = :last_name;"""


class SQLGenerator:
    def generate(self, intent, user_id):
        action = intent.get('intent', 'SELECT')
        table  = intent.get('table', 'patients')
        attrs  = intent.get('attributes') or {}

        SPECIAL_KEYS = {"aggregate", "order_by", "group_by", "join"}
        select_cols  = [k for k, v in attrs.items() if v is None and k not in SPECIAL_KEYS]
        filter_attrs = {k: v for k, v in attrs.items() if v is not None and k not in SPECIAL_KEYS}

        aggregate = attrs.get("aggregate")
        order_by  = attrs.get("order_by")
        group_by  = attrs.get("group_by")
        join      = attrs.get("join")

        user_context = f"\nid_user : {user_id}" if action == 'INSERT' else ""

        prompt = f"""Action : {action}
Table : {table}
Colonnes : {aggregate if aggregate else (select_cols if select_cols else 'toutes')}
Filtres : {filter_attrs if filter_attrs else 'aucun'}
GROUP BY : {group_by if group_by else 'aucun'}
ORDER BY : {order_by if order_by else 'aucun'}
JOIN : {join if join else 'aucun'}{user_context}

SQL :"""

        sql = ollama.generate('qwen2.5-coder:7b', prompt, system=SQL_SYSTEM, temperature=0.05)

        sql = sql.strip()
        for p in ['```sql', '```']:
            if sql.startswith(p):
                sql = sql[len(p):].strip()
        sql = sql.rstrip('`').strip()

        params = {**attrs}
        if action == 'INSERT':
            params['user_id'] = user_id
            params['id_user'] = user_id

        return {"sql": sql, "params": params}


sql_generator = SQLGenerator()

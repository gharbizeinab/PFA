from .ollama_client import ollama

SQL_SYSTEM = """You are Qwen, created by Alibaba Cloud. You are a PostgreSQL medical SQL expert. Generate ONLY valid SQL, nothing else.

ABSOLUTE RULES:
- Allowed: SELECT, INSERT, UPDATE only
- FORBIDDEN: DROP, TRUNCATE, ALTER, DELETE, GRANT, EXEC
- For soft delete: UPDATE table SET is_deleted=TRUE WHERE id=:id
- ALWAYS use bound parameters: :name, :value (never direct values)
- The AGE column exists directly in patients (INTEGER), NEVER use birthdate to calculate age
- Always end with a semicolon

TABLES:
patients(id_patient, id_user, first_name, last_name, birthdate, gender, age INTEGER, blood_group)
consultations(id_consultation, id_staff, id_patient, consultation_date, status, diagnosis, symptoms)
medical_records(id_record, id_patient, allergies, chronic_diseases, blood_group, height, weight)
ai_diagnosis(id_ai_diagnosis, id_consultation, predicted_disease, confidence_score)
appointments(id_appointment, id_patient, id_staff, appointment_date, reason, status)
medical_staffd(id_staff, id_user, id_service, name_staff, speciality)
services(id_service, service_name)

EXAMPLES:

Action: SELECT | Table: patients | Columns: all | Filters: none
→ SELECT * FROM patients;

Action: SELECT | Table: patients | Columns: [first_name, last_name] | Filters: none
→ SELECT first_name, last_name FROM patients;

Action: SELECT | Table: patients | Columns: COUNT(*) | Filters: none
→ SELECT COUNT(*) FROM patients;

Action: SELECT | Table: patients | Columns: COUNT(*) | Filters: {gender: :gender}
→ SELECT COUNT(*) FROM patients WHERE gender = :gender;

Action: SELECT | Table: patients | Columns: all | Filters: {gender: :gender}
→ SELECT * FROM patients WHERE gender = :gender;

Action: SELECT | Table: patients | Columns: AVG(age) | Filters: none
→ SELECT AVG(age) FROM patients;

Action: SELECT | Table: patients | Columns: all | Filters: {age: >70}
→ SELECT * FROM patients WHERE age > 70;

Action: SELECT | Table: patients | Columns: all | Filters: {age: <50}
→ SELECT * FROM patients WHERE age < 50;

Action: SELECT | Table: patients | Columns: all | ORDER BY: age DESC
→ SELECT * FROM patients ORDER BY age DESC;

Action: SELECT | Table: patients | Columns: [blood_group, COUNT(*)] | GROUP BY: blood_group
→ SELECT blood_group, COUNT(*) FROM patients GROUP BY blood_group;

Action: SELECT | Table: consultations | JOIN: patients | Columns: [first_name, last_name, diagnosis]
→ SELECT p.first_name, p.last_name, c.diagnosis FROM consultations c JOIN patients p ON c.id_patient = p.id_patient;

Action: INSERT | Table: patients | Values: {first_name: :first_name, last_name: :last_name, age: :age, id_user: :id_user}
→ INSERT INTO patients (id_user, first_name, last_name, age) VALUES (:id_user, :first_name, :last_name, :age);

Action: UPDATE | Table: patients | SET: {age: :age} | Filters: {first_name: :first_name, last_name: :last_name}
→ UPDATE patients SET age = :age WHERE first_name = :first_name AND last_name = :last_name;"""


class SQLGenerator:
    def generate(self, intent, user_id):
        action    = intent.get('intent', 'SELECT')
        table     = intent.get('table', 'patients')
        attrs     = intent.get('attributes') or {}
        staff_ids = intent.get('_staff_ids', [])
        today     = intent.get('_today')

        # ── Consultations filtered by doctor name (JOIN medical_staff + users) ──
        if table == 'consultations' and action == 'SELECT' and 'name_staff' in attrs:
            name_val = attrs.get('name_staff') or ''
            date_val = attrs.get('consultation_date', '')
            from datetime import date as _date
            import re as _re
            if str(date_val).lower() in ('today', "aujourd'hui", str(_date.today())):
                date_val = _date.today().isoformat()
            # Strip honorific titles (Dr., Mr., Mrs.) for flexible matching
            clean_name = _re.sub(r'^(Dr\.?|M\.?|Mr\.?|Mrs\.?|Ms\.?)\s+', '', name_val, flags=_re.I).strip()
            # Match by professional name_staff OR user account name (first_name + last_name)
            name_filter = (
                "(ms.name_staff ILIKE :name_staff "
                "OR u.first_name || ' ' || u.last_name ILIKE :name_staff)"
            )
            where = [name_filter]
            params = {"name_staff": f"%{clean_name}%"}
            if date_val:
                where.append("c.consultation_date = :consultation_date")
                params["consultation_date"] = date_val
            sql = (
                f"SELECT c.consultation_date, c.status, c.diagnosis, c.symptoms, "
                f"p.first_name || ' ' || p.last_name AS patient_name, p.age, p.gender "
                f"FROM consultations c "
                f"JOIN medical_staff ms ON c.id_staff = ms.id_staff "
                f"JOIN users u ON ms.id_user = u.id_user "
                f"JOIN patients p ON c.id_patient = p.id_patient "
                f"WHERE {' AND '.join(where)} "
                f"ORDER BY c.consultation_date DESC;"
            )
            return {"sql": sql, "params": params}

        # ── Contextual SQL for appointments filtered by connected doctor + today ──
        if table == 'appointments' and staff_ids and action == 'SELECT':
            ph        = ', '.join([f':sid{i}' for i in range(len(staff_ids))])
            ph_params = {f'sid{i}': sid for i, sid in enumerate(staff_ids)}
            sql = (
                f"SELECT a.*, p.first_name || ' ' || p.last_name AS patient_name "
                f"FROM appointments a "
                f"JOIN patients p ON a.id_patient = p.id_patient "
                f"WHERE a.id_staff IN ({ph}) AND a.appointment_date = :today "
                f"ORDER BY a.appointment_time;"
            )
            return {"sql": sql, "params": {**ph_params, "today": today}}

        SPECIAL_KEYS = {"aggregate", "order_by", "group_by", "join"}
        select_cols  = [k for k, v in attrs.items() if v is None and k not in SPECIAL_KEYS]
        filter_attrs = {k: v for k, v in attrs.items() if v is not None and k not in SPECIAL_KEYS}

        aggregate = attrs.get("aggregate")
        order_by  = attrs.get("order_by")
        group_by  = attrs.get("group_by")
        join      = attrs.get("join")

        user_context = f"\nid_user : {user_id}" if action == 'INSERT' else ""

        prompt = f"""Action: {action}
Table: {table}
Columns: {aggregate if aggregate else (select_cols if select_cols else 'all')}
Filters: {filter_attrs if filter_attrs else 'none'}
GROUP BY: {group_by if group_by else 'none'}
ORDER BY: {order_by if order_by else 'none'}
JOIN: {join if join else 'none'}{user_context}

SQL:"""

        sql = ollama.chat('qwen2.5-coder:7b', prompt, system=SQL_SYSTEM,
                          temperature=0.1, top_p=0.95, top_k=40, num_predict=2048)

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

from .ollama_client import ollama

SQL_SYSTEM = """Expert SQL PostgreSQL médical. Génère UNIQUEMENT du SQL valide, rien d'autre.

RÈGLES ABSOLUES :
- Autorisé : SELECT, INSERT, UPDATE uniquement
- INTERDIT : DROP, TRUNCATE, ALTER, DELETE, GRANT, EXEC
- Pour supprimer : UPDATE table SET is_deleted=TRUE WHERE id=:id
- Utilise TOUJOURS des paramètres liés : :nom, :prenom (jamais de valeurs directes)
- Termine par un point-virgule

TABLES PRINCIPALES :
patients(id_patient, id_user, first_name, last_name, birthdate, gender, age INTEGER, blood_group)
consultations(id_consultation, id_staff, id_patient, consultation_date, status, diagnosis, symptoms)
medical_records(id_record, id_patient, allergies, chronic_diseases, blood_group, height, weight)
ai_diagnosis(id_ai_diagnosis, id_consultation, predicted_disease, confidence_score)
appointments(id_appointment, id_patient, id_staff, appointment_date, reason, status)
medical_staff(id_staff, id_user, id_service, name_staff, speciality)
services(id_service, service_name)

RÈGLES IMPORTANTES :
- La colonne AGE existe directement dans patients (INTEGER). N'utilise JAMAIS birthdate pour calculer l'âge.
- "count" / "number of" / "total" → toujours SELECT COUNT(*)
- "show names" / "show X" → SELECT X (jamais SELECT *)
- "sorted" / "order by" → toujours utiliser ORDER BY
- "average" → AVG(colonne), "oldest" → MAX(age), "youngest" → MIN(age)

EXEMPLES (apprends le pattern, pas la réponse) :

# Afficher toutes les colonnes
"list all patients" → SELECT * FROM patients;
"show all consultations" → SELECT * FROM consultations;
"list all medical staff" → SELECT * FROM medical_staff;

# Afficher des colonnes spécifiques → SELECT col1, col2 (jamais SELECT * ni WHERE)
"show first and last names of patients" → SELECT first_name, last_name FROM patients;
"show names of all staff" → SELECT name_staff FROM medical_staff;
"show patient age and gender" → SELECT age, gender FROM patients;
"show service names" → SELECT service_name FROM services;
"show all service names" → SELECT service_name FROM services;
"show staff specialties" → SELECT DISTINCT speciality FROM medical_staff;

# Compter → SELECT COUNT(*) TOUJOURS
"count total patients" → SELECT COUNT(*) FROM patients;
"count total staff" → SELECT COUNT(*) FROM medical_staff;
"count total consultations" → SELECT COUNT(*) FROM consultations;
"find number of female patients" → SELECT COUNT(*) FROM patients WHERE gender = :gender;
"find number of male patients" → SELECT COUNT(*) FROM patients WHERE gender = :gender;

# Filtrer par valeur → WHERE colonne = :param
"find female patients" → SELECT * FROM patients WHERE gender = :gender;
"show patients older than 70" → SELECT first_name, last_name, age FROM patients WHERE age > 70;
"find patients with hypertension" → SELECT p.first_name, p.last_name FROM patients p JOIN medical_records r ON p.id_patient = r.id_patient WHERE r.chronic_diseases ILIKE :disease;

# Agrégation → AVG, MAX, MIN — utiliser la colonne age INTEGER directement
"show average patient age" → SELECT AVG(age) FROM patients;
"show average age by gender" → SELECT gender, AVG(age) FROM patients GROUP BY gender;
"find oldest patient" → SELECT first_name, last_name, age FROM patients WHERE age = (SELECT MAX(age) FROM patients);
"find youngest patient" → SELECT first_name, last_name, age FROM patients WHERE age = (SELECT MIN(age) FROM patients);
"show patients older than 70" → SELECT first_name, last_name, age FROM patients WHERE age > 70;
"show patients younger than 50" → SELECT first_name, last_name, age FROM patients WHERE age < 50;

# Trier → ORDER BY — utiliser la colonne age directement
"show patients sorted by age descending" → SELECT first_name, last_name, age FROM patients ORDER BY age DESC;
"show patients sorted by age ascending" → SELECT first_name, last_name, age FROM patients ORDER BY age ASC;
"show staff sorted alphabetically" → SELECT name_staff FROM medical_staff ORDER BY name_staff ASC;

# Grouper → GROUP BY
"count patients by blood group" → SELECT blood_group, COUNT(*) FROM patients GROUP BY blood_group;
"average age by gender" → SELECT gender, AVG(age) FROM patients GROUP BY gender;

# Jointure → JOIN
"show consultations with patient names" → SELECT p.first_name, p.last_name, c.diagnosis FROM consultations c JOIN patients p ON c.id_patient = p.id_patient;
"show staff working in Oncology" → SELECT m.name_staff, m.speciality FROM medical_staff m JOIN services s ON m.id_service = s.id_service WHERE s.service_name = :service_name;

# INSERT → utilise :id_user pour la colonne id_user
"add patient Youssef Mansour aged 45 male" → INSERT INTO patients (id_user, first_name, last_name, age, gender) VALUES (:id_user, :first_name, :last_name, :age, :gender);
"add service Neurology" → INSERT INTO services (service_name) VALUES (:service_name);

# UPDATE → WHERE avec paramètre lié
"update age of Mohamed Trabelsi to 50" → UPDATE patients SET age = :age WHERE first_name = :first_name AND last_name = :last_name;
"change diagnosis of consultation 1" → UPDATE consultations SET diagnosis = :diagnosis WHERE id_consultation = :id_consultation;"""

class SQLGenerator:
    def generate(self, intent, user_id, question=""):
        action = intent.get('intent', 'SELECT')
        table  = intent.get('table', 'patients')
        attrs  = intent.get('attributes') or {}

        # Séparer les colonnes à afficher (valeur null) des filtres (valeur non-null)
        select_cols  = [k for k, v in attrs.items() if v is None]
        filter_attrs = {k: v for k, v in attrs.items() if v is not None}

        # Alerte age uniquement pour les comparaisons/extremes (pas pour ORDER BY)
        q_lower = question.lower()
        age_hint = ""
        if any(w in q_lower for w in ['older than', 'younger than', 'oldest', 'youngest']):
            age_hint = "\n⚠️ Utilise UNIQUEMENT la colonne age (INTEGER) pour les conditions et le SELECT. N'utilise JAMAIS birthdate ni EXTRACT ni AGE()."

        user_context = f"\nUtilisateur courant (id_user) : {user_id}" if action == 'INSERT' else ""

        prompt = f"""Question originale : {question}
Action : {action}
Table : {table}
Colonnes à afficher : {select_cols if select_cols else 'toutes (*)'}
Filtres WHERE : {filter_attrs if filter_attrs else 'aucun'}{age_hint}{user_context}

SQL PostgreSQL uniquement :"""

        sql = ollama.generate('qwen2.5-coder:7b', prompt, system=SQL_SYSTEM, temperature=0.05)

        sql = sql.strip()
        for p in ['```sql','```']:
            if sql.startswith(p): sql = sql[len(p):].strip()
        sql = sql.rstrip('`').strip()

        params = {**attrs}
        if action == 'INSERT':
            params['user_id'] = user_id
            params['id_user'] = user_id

        return {"sql": sql, "params": params}

sql_generator = SQLGenerator()
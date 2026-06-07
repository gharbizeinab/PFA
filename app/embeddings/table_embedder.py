from sentence_transformers import SentenceTransformer
import faiss, numpy as np, pickle, os

TABLE_DESCRIPTIONS = {
    "patients":         "patients count how many total number. Demographics: age gender male female blood group A+ B+ O+ AB+. List find filter show all patients. Oldest youngest average age older younger than. First name last name.",
    "consultations":    "Medical consultations and clinical visits. Diagnosis, symptoms, treatment, prescription, date, status. List all consultations joined with patient names.",
    "medical_records":  "Medical records: health background, allergies, chronic diseases, diabetes, hypertension. Blood type, height, weight, BMI.",
    "ai_diagnosis":     "AI predicted diagnosis. Disease prediction confidence score recommendation symptom analysis.",
    "appointments":     "Doctor-patient scheduled appointments and visits. Appointment date reason status: pending completed cancelled. Upcoming past appointments.",
    "medical_staff":    "Medical team healthcare workers: doctors nurses caregivers. Name speciality department. List alphabetically.",
    "services":         "Hospital departments and care units. Available service names offered by the hospital.",
    "medical_documents":"Patient files: x-rays, prescriptions, PDF attachments and medical documents.",
    "users":            "System user accounts. Show email, role, access level and login information.",
    "notifications":    "System alerts, reminder messages and notifications sent to users.",
    "audit_logs":       "Security audit trail. Who did what action, traceability and history of system operations.",
    "ai_chat_history":  "History of AI chatbot conversations, questions asked and answers given.",
}

INDEX_PATH = "app/embeddings/faiss_index.pkl"

# Keyword fallback: if query contains these words, force the table regardless of FAISS score
KEYWORD_HINTS = {
    "patients":        ["patient", "patients"],
    "appointments":    ["appointment", "appointments"],
    "consultations":   ["consultation", "consultations"],
    "medical_records": ["medical record", "medical records"],
    "medical_staff":   ["medical staff", "staff member", "staff members"],
    "services":        ["service", "services"],
    "ai_diagnosis":    ["ai diagnosis", "predicted disease"],
    "audit_logs":      ["audit log", "audit trail"],
}


class TableMatcher:
    def __init__(self):
        self.model = None; self.index = None
        self.tables = list(TABLE_DESCRIPTIONS.keys())

    def _load_model(self):
        if not self.model:
            self.model = SentenceTransformer('FremyCompany/BioLORD-2023-C')

    def build_index(self):
        self._load_model()
        emb = self.model.encode(list(TABLE_DESCRIPTIONS.values()), normalize_embeddings=True)
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb.astype(np.float32))
        with open(INDEX_PATH, 'wb') as f:
            pickle.dump({'idx': faiss.serialize_index(self.index), 'tbl': self.tables}, f)
        print("✓ FAISS index built")

    def _ensure_loaded(self):
        if self.index: return
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, 'rb') as f: d = pickle.load(f)
            self.index = faiss.deserialize_index(d['idx']); self.tables = d['tbl']
            self._load_model()
        else: self.build_index()

    def _keyword_hint(self, query: str):
        q = query.lower()
        for table, keywords in KEYWORD_HINTS.items():
            if any(kw in q for kw in keywords):
                return table
        return None

    def find(self, query, k=3):
        self._ensure_loaded()

        hint = self._keyword_hint(query)

        v = self.model.encode([query], normalize_embeddings=True)
        scores, idxs = self.index.search(v.astype(np.float32), k)
        results = [(self.tables[i], round(float(s), 3)) for s, i in zip(scores[0], idxs[0]) if i != -1 and s > 0.3]

        # Keyword fallback only when FAISS finds nothing above threshold
        if not results:
            return [(hint, 0.5)] if hint else []

        return results

table_matcher = TableMatcher()
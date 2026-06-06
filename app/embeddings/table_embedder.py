from sentence_transformers import SentenceTransformer
import faiss, numpy as np, pickle, os

TABLE_DESCRIPTIONS = {
    "patients":         "patients list all count total number find show select demographics age gender male female sex oldest youngest average older younger blood group first name last name identity hospitalized statistics",
    "consultations":    "consultations list all count total doctor visits clinical encounters diagnosis treatment prescription symptoms date",
    "medical_records":  "patient health background allergies chronic diseases blood type height weight body measurements BMI show list all records",
    "ai_diagnosis":     "AI diagnosis predicted disease confidence score recommendation symptom analysis",
    "appointments":     "appointments scheduling agenda date time slot status list all count",
    "medical_staff":    "medical staff doctors nurses caregivers list all count total number members speciality sorted alphabetically",
    "services":         "services list all show service names count total hospital departments units",
    "medical_documents":"files x-rays prescriptions PDF medical documents attachments",
    "users":            "user accounts email role access login system",
    "notifications":    "alerts system messages reminders notifications",
    "audit_logs":       "traceability history actions who did what security logs",
    "ai_chat_history":  "conversation history AI questions asked answers chatbot",
}

INDEX_PATH = "app/embeddings/faiss_index.pkl"

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
        print("✓ Index FAISS construit")

    def _ensure_loaded(self):
        if self.index: return
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, 'rb') as f: d = pickle.load(f)
            self.index = faiss.deserialize_index(d['idx']); self.tables = d['tbl']
            self._load_model()
        else: self.build_index()

    def find(self, query, k=3):
        self._ensure_loaded()
        v = self.model.encode([query], normalize_embeddings=True)
        scores, idxs = self.index.search(v.astype(np.float32), k)
        return [(self.tables[i], round(float(s),3)) for s,i in zip(scores[0],idxs[0]) if i!=-1 and s>0.3]

table_matcher = TableMatcher()
from sentence_transformers import SentenceTransformer
import faiss, numpy as np, pickle, os

TABLE_DESCRIPTIONS = {
    "patients":         "patients malades hospitalisés identité âge genre groupe sanguin contact",
    "consultations":    "consultations visites médicales actes cliniques diagnostic traitement symptômes",
    "medical_records":  "dossier médical allergies maladies chroniques antécédents médicaments poids taille",
    "ai_diagnosis":     "diagnostic IA maladie prédite score confiance recommandation analyse symptômes",
    "appointments":     "rendez-vous planification agenda date horaire statut",
    "medical_staff":    "médecins infirmiers personnel soignant spécialité licence",
    "services":         "services hospitaliers cardiologie oncologie unités de soins",
    "medical_documents":"fichiers radios ordonnances PDF documents médicaux attachments",
    "users":            "comptes utilisateurs email rôle accès connexion système",
    "notifications":    "alertes messages système rappels notifications",
    "audit_logs":       "traçabilité historique actions qui a fait quoi sécurité",
    "ai_chat_history":  "historique conversations IA questions posées réponses chatbot",
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
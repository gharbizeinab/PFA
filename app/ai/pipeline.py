from .intent_classifier import intent_classifier
from .attribute_extractor import attribute_extractor
from .field_validator import field_validator
from .clarifier import clarifier
from ..embeddings.table_embedder import table_matcher


class MedicalPipeline:
    def run(self, query: str, history: list = [], pending_context: dict = None) -> dict:
        """
        Cas multi-tour : si pending_context est fourni (intent + table déjà connus),
        on saute les étapes 1 et 2 et on complète uniquement les attributs manquants.
        """
        if pending_context:
            return self._refine(query, pending_context)
        return self._full_run(query, history)

    def _full_run(self, query: str, history: list) -> dict:
        # Étape 1 — Intent (mots-clés Python, Llama en fallback)
        intent = intent_classifier.classify(query)

        if intent == 'QUESTION':
            return self._question_response()

        # Étape 2 — Table (BioLORD + FAISS)
        matches = table_matcher.find(query, k=1)
        if not matches:
            return {
                "intent": intent, "table": None, "attributes": {},
                "missing_fields": [], "needs_clarification": True,
                "clarification_question": "Sur quelle table souhaitez-vous effectuer cette opération ?",
                "confidence": 0.0
            }
        table, score = matches[0]

        # Étape 3 — Extraction attributs (Llama — un seul prompt focalisé)
        attributes = attribute_extractor.extract(query, table, intent)

        # Étape 4 — Champs manquants (Python pur)
        missing = field_validator.get_missing(table, attributes, intent)

        # Étape 5 — Question de clarification (Llama — seulement si nécessaire)
        clarification_question = clarifier.ask(table, missing, attributes) if missing else None

        return {
            "intent": intent,
            "table": table,
            "attributes": attributes,
            "missing_fields": missing,
            "needs_clarification": bool(missing),
            "clarification_question": clarification_question,
            "confidence": round(score, 3)
        }

    def _refine(self, query: str, pending: dict) -> dict:
        """Multi-tour : extrait les nouveaux attributs depuis la réponse de l'utilisateur
        et les fusionne avec ceux déjà connus."""
        table = pending.get('table')
        intent = pending.get('intent')

        new_attrs = attribute_extractor.extract(query, table, intent)
        merged = {**pending.get('attributes', {}), **new_attrs}

        missing = field_validator.get_missing(table, merged, intent)
        clarification_question = clarifier.ask(table, missing, merged) if missing else None

        return {
            "intent": intent,
            "table": table,
            "attributes": merged,
            "missing_fields": missing,
            "needs_clarification": bool(missing),
            "clarification_question": clarification_question,
            "confidence": pending.get('confidence', 0.9)
        }

    def _question_response(self) -> dict:
        return {
            "intent": "QUESTION", "table": None, "attributes": {},
            "missing_fields": [], "needs_clarification": True,
            "clarification_question": (
                "Je suis un assistant médical. "
                "Posez-moi une question sur les patients, consultations ou rendez-vous."
            ),
            "confidence": 0.5
        }


pipeline = MedicalPipeline()

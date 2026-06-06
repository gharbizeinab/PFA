from .intent_classifier import intent_classifier
from .attribute_extractor import attribute_extractor
from .field_validator import field_validator
from .clarifier import clarifier
from ..embeddings.table_embedder import table_matcher


class MedicalPipeline:
    def run(self, query: str, history: list = [], pending_context: dict = None) -> dict:
        """
        Multi-turn: if pending_context is provided (intent + table already known),
        skip steps 1 and 2 and only complete the missing attributes.
        """
        if pending_context:
            return self._refine(query, pending_context)
        return self._full_run(query, history)

    def _full_run(self, query: str, history: list) -> dict:
        # Step 1 — Intent (Python keywords, Llama as fallback)
        intent = intent_classifier.classify(query)

        if intent == 'QUESTION':
            return self._question_response()

        # Step 2 — Table (BioLORD + FAISS)
        matches = table_matcher.find(query, k=3)
        if not matches:
            return {
                "intent": intent, "table": None, "attributes": {},
                "missing_fields": [], "needs_clarification": True,
                "clarification_question": "Which table would you like to operate on?",
                "confidence": 0.0
            }
        table, score = matches[0]

        # Step 3 — Attribute extraction (Llama — focused prompt)
        attributes = attribute_extractor.extract(query, table, intent)

        # Step 4 — Missing fields (pure Python)
        missing = field_validator.get_missing(table, attributes, intent)

        # Step 5 — Clarification question (Llama — only if needed)
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
        """Multi-turn: extract new attributes from the user's response
        and merge them with the already known ones."""
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
                "I am a medical assistant. "
                "Ask me a question about patients, consultations or appointments."
            ),
            "confidence": 0.5
        }


pipeline = MedicalPipeline()

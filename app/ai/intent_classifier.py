from .ollama_client import ollama

INSERT_KW = ['ajoute', 'ajouter', 'crée', 'créer', 'enregistre', 'enregistrer',
             'nouveau', 'nouvelle', 'insère', 'insérer', 'add', 'insert', 'create',
             'nouvel', 'saisir', 'saisie']
UPDATE_KW = ['modifie', 'modifier', 'change', 'changer', 'met à jour', 'mettre à jour',
             'mise à jour', 'update', 'corrige', 'corriger', 'mets à jour']
SELECT_KW = ['montre', 'montrer', 'liste', 'lister', 'affiche', 'afficher', 'trouve',
             'trouver', 'cherche', 'chercher', 'show', 'list', 'find', 'get', 'select',
             'donne', 'donner', 'quels', 'quelles', 'combien', 'quel', 'quelle',
             'afficher', 'voir', 'consulter', 'rechercher']

FALLBACK_SYSTEM = """Classifie cette requête médicale. Réponds UNIQUEMENT par un seul mot parmi :
SELECT, INSERT, UPDATE, QUESTION"""


class IntentClassifier:
    def classify(self, query: str) -> str:
        q = query.lower()

        if any(k in q for k in INSERT_KW):
            return 'INSERT'
        if any(k in q for k in UPDATE_KW):
            return 'UPDATE'
        if any(k in q for k in SELECT_KW):
            return 'SELECT'

        # Fallback LLM uniquement si aucun mot-clé ne correspond
        raw = ollama.generate('llama3.2:3b', query, system=FALLBACK_SYSTEM, temperature=0.0)
        result = raw.strip().upper().split()[0] if raw.strip() else ''
        return result if result in ('SELECT', 'INSERT', 'UPDATE', 'QUESTION') else 'QUESTION'


intent_classifier = IntentClassifier()

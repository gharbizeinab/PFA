from .ollama_client import ollama

INSERT_KW = ['ajoute', 'ajouter', 'crée', 'créer', 'enregistre', 'enregistrer',
             'nouveau', 'nouvelle', 'insère', 'insérer', 'nouvel', 'saisir', 'saisie',
             'add', 'insert', 'create', 'register', 'new', 'record']
UPDATE_KW = ['modifie', 'modifier', 'change', 'changer', 'met à jour', 'mettre à jour',
             'mise à jour', 'corrige', 'corriger', 'mets à jour',
             'update', 'edit', 'modify', 'correct', 'set']
SELECT_KW = ['montre', 'montrer', 'liste', 'lister', 'affiche', 'afficher', 'trouve',
             'trouver', 'cherche', 'chercher', 'donne', 'donner', 'quels', 'quelles',
             'combien', 'quel', 'quelle', 'afficher', 'voir', 'consulter', 'rechercher',
             'show', 'list', 'find', 'get', 'select', 'display', 'retrieve',
             'count', 'average', 'total', 'how many', 'what', 'which', 'calculate',
             'search', 'fetch', 'view', 'all', 'give']

FALLBACK_SYSTEM = """Classify this medical request. Reply ONLY with one single word from:
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

        # LLM fallback only if no keyword matched
        raw = ollama.chat('llama3.2:3b', query, system=FALLBACK_SYSTEM,
                          temperature=0.0, top_p=0.9, num_predict=16)
        result = raw.strip().upper().split()[0] if raw.strip() else ''
        return result if result in ('SELECT', 'INSERT', 'UPDATE', 'QUESTION') else 'QUESTION'


intent_classifier = IntentClassifier()

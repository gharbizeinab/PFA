from .ollama_client import ollama

SYSTEM = """Tu es un assistant médical. Génère une seule question courte et polie en français
pour demander les informations manquantes. Réponds UNIQUEMENT avec la question, rien d'autre."""


class Clarifier:
    def ask(self, table: str, missing_fields: list, attributes: dict) -> str:
        known = ', '.join(f"{k}={v}" for k, v in attributes.items() if v is not None)
        prompt = f"""Table : {table}
Informations déjà connues : {known or 'aucune'}
Champs manquants : {', '.join(missing_fields)}

Génère une question pour demander les informations manquantes."""

        return ollama.generate('llama3.2:3b', prompt, system=SYSTEM, temperature=0.2)


clarifier = Clarifier()

from .ollama_client import ollama

SYSTEM = """You are a medical assistant. Generate one short and polite question
to ask for the missing information. Reply ONLY with the question, nothing else."""


class Clarifier:
    def ask(self, table: str, missing_fields: list, attributes: dict) -> str:
        known = ', '.join(f"{k}={v}" for k, v in attributes.items() if v is not None)
        prompt = f"""Table: {table}
Already known information: {known or 'none'}
Missing fields: {', '.join(missing_fields)}

Generate a question to ask for the missing information."""

        return ollama.chat('llama3.2:3b', prompt, system=SYSTEM,
                           temperature=0.5, top_p=0.9, num_predict=120)


clarifier = Clarifier()

import os
import requests

class OllamaClient:
    def __init__(self, base_url=None):
        if base_url is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = base_url.rstrip("/")

    def generate(self, model, prompt, system=None, temperature=0.1):
        payload = {
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": temperature, "num_predict": 512}
        }
        if system:
            payload["system"] = system
        try:
            r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=90)
            r.raise_for_status()
            return r.json()["response"].strip()
        except requests.exceptions.ConnectionError:
            raise Exception("❌ Ollama non démarré. Lance : ollama serve")
        except Exception as e:
            raise Exception(f"❌ Erreur Ollama : {e}")

    def is_running(self):
        try: return requests.get(self.base_url, timeout=3).status_code == 200
        except: return False

ollama = OllamaClient()  # singleton global
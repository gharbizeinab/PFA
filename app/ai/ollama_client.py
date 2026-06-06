import os
import requests

class OllamaClient:
    def __init__(self, base_url=None):
        if base_url is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = base_url.rstrip("/")

    def chat(self, model, user_message, system=None, temperature=0.1,
             top_p=None, top_k=None, num_predict=1024):
        """Chat format — native format for Instruct models (Llama 3.2, Qwen Instruct)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_message})

        options = {"temperature": temperature, "num_predict": num_predict}
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=90)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            raise Exception("Ollama not running. Run: ollama serve")
        except Exception as e:
            raise Exception(f"Ollama error: {e}")

    def generate(self, model, prompt, system=None, temperature=0.1,
                 top_p=None, top_k=None, num_predict=512):
        """Raw generate — kept for backward compatibility."""
        options = {"temperature": temperature, "num_predict": num_predict}
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k

        payload = {
            "model": model, "prompt": prompt, "stream": False,
            "options": options,
        }
        if system:
            payload["system"] = system
        try:
            r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=90)
            r.raise_for_status()
            return r.json()["response"].strip()
        except requests.exceptions.ConnectionError:
            raise Exception("Ollama not running. Run: ollama serve")
        except Exception as e:
            raise Exception(f"Ollama error: {e}")

    def is_running(self):
        try: return requests.get(self.base_url, timeout=3).status_code == 200
        except: return False

ollama = OllamaClient()

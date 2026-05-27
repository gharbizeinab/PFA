import json
from datetime import datetime

class ConversationMemory:
    TTL = 1800  # 30 minutes

    def __init__(self, redis_client):
        self.r = redis_client

    def get_history(self, sid):
        d = self.r.get(f"conv:{sid}")
        return json.loads(d) if d else []

    def add_message(self, sid, role, content):
        h = self.get_history(sid)
        h.append({"role":role, "content":content, "time":datetime.now().isoformat()})
        self.r.setex(f"conv:{sid}", self.TTL, json.dumps(h[-20:], ensure_ascii=False))

    def save_pending(self, sid, intent):
        self.r.setex(f"pending:{sid}", 600, json.dumps(intent, ensure_ascii=False))

    def get_pending(self, sid):
        d = self.r.get(f"pending:{sid}")
        return json.loads(d) if d else None

    def clear_pending(self, sid):
        self.r.delete(f"pending:{sid}")
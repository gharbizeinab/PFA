from sqlalchemy import text
from .. import db

class SQLExecutor:
    def execute(self, sql, params={}):
        """Exécute le SQL de façon sécurisée avec paramètres liés."""
        try:
            with db.engine.connect() as conn:
                with conn.begin():
                    r = conn.execute(text(sql), params)
                    if sql.strip().upper().startswith('SELECT'):
                        rows = r.fetchall(); cols = list(r.keys())
                        return {"ok":True, "data":[dict(zip(cols,row)) for row in rows]}
                    return {"ok":True, "data":[], "affected":r.rowcount}
        except Exception as e:
            msg = str(e)
            if 'NotNullViolation' in msg or 'null value in column' in msg:
                col = msg.split('column "')[1].split('"')[0] if 'column "' in msg else 'inconnu'
                clean = f"Champ obligatoire manquant : '{col}'. Précise cette information dans ta demande."
            elif 'UniqueViolation' in msg or 'duplicate key' in msg:
                clean = "Cette entrée existe déjà dans la base de données."
            elif 'ForeignKeyViolation' in msg or 'foreign key' in msg:
                clean = "Référence invalide : un identifiant lié n'existe pas."
            elif 'UndefinedTable' in msg or 'relation' in msg and 'does not exist' in msg:
                clean = "Table introuvable. Vérifie le nom de la table."
            elif 'UndefinedColumn' in msg or 'column' in msg and 'does not exist' in msg:
                col = msg.split('column "')[1].split('"')[0] if 'column "' in msg else 'inconnue'
                clean = f"Colonne '{col}' introuvable dans cette table."
            else:
                clean = "Erreur base de données. Reformule ta demande."
            return {"ok": False, "data": [], "error": clean}

sql_executor = SQLExecutor()
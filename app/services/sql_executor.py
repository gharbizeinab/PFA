from sqlalchemy import text
from .. import db

class SQLExecutor:
    def execute(self, sql, params={}):
        """Execute SQL securely with bound parameters."""
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
                col = msg.split('column "')[1].split('"')[0] if 'column "' in msg else 'unknown'
                clean = f"Required field missing: '{col}'. Please provide this information."
            elif 'UniqueViolation' in msg or 'duplicate key' in msg:
                clean = "This entry already exists in the database."
            elif 'ForeignKeyViolation' in msg or 'foreign key' in msg:
                clean = "Invalid reference: a linked identifier does not exist."
            elif 'UndefinedTable' in msg or 'relation' in msg and 'does not exist' in msg:
                clean = "Table not found. Please check the table name."
            elif 'UndefinedColumn' in msg or 'column' in msg and 'does not exist' in msg:
                col = msg.split('column "')[1].split('"')[0] if 'column "' in msg else 'unknown'
                clean = f"Column '{col}' not found in this table."
            else:
                clean = "Database error. Please rephrase your request."
            return {"ok": False, "data": [], "error": clean}

sql_executor = SQLExecutor()
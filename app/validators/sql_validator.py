import sqlglot
from sqlglot import exp

FORBIDDEN_KW = ['DROP','TRUNCATE','ALTER','GRANT','REVOKE','EXEC','EXECUTE','--',';--']
FORBIDDEN_TYPES = {exp.Drop, exp.TruncateTable, exp.Create, exp.AlterTable}
class SQLValidator:
    def validate(self, sql, allowed_tables, action='SELECT'):
        """Valide le SQL. Retourne {"valid": bool, "error": str|None}"""
        # 1. Mots-clés dangereux
        sql_up = sql.upper()
        for kw in FORBIDDEN_KW:
            if kw in sql_up:
                return {"valid":False, "error":f"Opération interdite : {kw}"}
        # 2. Parser
        try:
            parsed = sqlglot.parse(sql, dialect="postgres")
        except Exception as e:
            return {"valid":False, "error":f"SQL invalide : {e}"}
        # 3. Types interdits
        for stmt in parsed:
            if type(stmt) in FORBIDDEN_TYPES:
                return {"valid":False, "error":f"Statement interdit : {type(stmt).__name__}"}
        # 4. Tables autorisées
        if allowed_tables:
            for stmt in parsed:
                for tbl in stmt.find_all(exp.Table):
                    if tbl.name.lower() not in allowed_tables:
                        return {"valid":False, "error":f"Table non autorisée : {tbl.name}"}
        return {"valid":True, "error":None}

sql_validator = SQLValidator()
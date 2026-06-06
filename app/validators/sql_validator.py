import sqlglot
from sqlglot import exp

FORBIDDEN_KW = ['DROP','TRUNCATE','ALTER','GRANT','REVOKE','EXEC','EXECUTE','--',';--']
FORBIDDEN_TYPES = {exp.Drop, exp.TruncateTable, exp.Create, exp.AlterTable}
class SQLValidator:
    def validate(self, sql, allowed_tables, action='SELECT'):
        """Validate SQL. Returns {"valid": bool, "error": str|None}"""
        # 1. Forbidden keywords
        sql_up = sql.upper()
        for kw in FORBIDDEN_KW:
            if kw in sql_up:
                return {"valid":False, "error":f"Forbidden operation: {kw}"}
        # 2. Parser
        try:
            parsed = sqlglot.parse(sql, dialect="postgres")
        except Exception as e:
            return {"valid":False, "error":f"Invalid SQL: {e}"}
        # 3. Forbidden statement types
        for stmt in parsed:
            if type(stmt) in FORBIDDEN_TYPES:
                return {"valid":False, "error":f"Forbidden statement: {type(stmt).__name__}"}
        # 4. Allowed tables
        if allowed_tables:
            for stmt in parsed:
                for tbl in stmt.find_all(exp.Table):
                    if tbl.name.lower() not in allowed_tables:
                        return {"valid":False, "error":f"Unauthorized table: {tbl.name}"}
        return {"valid":True, "error":None}

sql_validator = SQLValidator()
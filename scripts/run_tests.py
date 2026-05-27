"""
Script de test automatique — compare SQL généré vs SQL attendu
Usage : python scripts/run_tests.py
"""

import requests
import json
import time
import re

API = "http://localhost:5000"

QUESTIONS = [
    {"question": "List all patients",                          "expected": "SELECT * FROM patients"},
    {"question": "Show first and last names of all patients",  "expected": "SELECT first_name, last_name FROM patients"},
    {"question": "Find all female patients",                   "expected": "SELECT * FROM patients WHERE gender"},
    {"question": "Find all male patients",                     "expected": "SELECT * FROM patients WHERE gender"},
    {"question": "Show patients older than 70",                "expected": "WHERE age"},
    {"question": "Show patients younger than 50",              "expected": "WHERE age"},
    {"question": "Count total number of patients",             "expected": "SELECT COUNT(*)"},
    {"question": "Find the oldest patient",                    "expected": "MAX(age)"},
    {"question": "Find the youngest patient",                  "expected": "MIN(age)"},
    {"question": "Show average patient age",                   "expected": "AVG(age)"},
    {"question": "List all services",                          "expected": "SELECT * FROM services"},
    {"question": "Show all service names",                     "expected": "SELECT service_name FROM services"},
    {"question": "Count total services",                       "expected": "SELECT COUNT(*)"},
    {"question": "List all medical staff",                     "expected": "SELECT * FROM medical_staff"},
    {"question": "Count total staff members",                  "expected": "SELECT COUNT(*)"},
    {"question": "List all consultations",                     "expected": "SELECT * FROM consultations"},
    {"question": "Count total consultations",                  "expected": "SELECT COUNT(*)"},
    {"question": "Show all medical records",                   "expected": "SELECT * FROM medical_records"},
    {"question": "Show average age by gender",                 "expected": "AVG(age)"},
    {"question": "Show patients sorted by age descending",     "expected": "ORDER BY age"},
    {"question": "Show staff sorted alphabetically",           "expected": "ORDER BY name_staff"},
    {"question": "Find number of female patients",             "expected": "COUNT(*)"},
    {"question": "Find number of male patients",               "expected": "COUNT(*)"},
    {"question": "Count patients by blood group",              "expected": "GROUP BY blood_group"},
    {"question": "Show all consultations with patient names",  "expected": "JOIN patients"},
]

def login():
    r = requests.post(f"{API}/api/auth/login",
                      json={"username": "admin", "password": "admin123"})
    return r.json()["token"]

def test_question(token, question, expected_keyword):
    r = requests.post(
        f"{API}/api/chat/message",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"message": question}
    )
    data = r.json()
    sql = data.get("sql", "") or ""
    ok  = expected_keyword.upper() in sql.upper()
    return sql, ok

def main():
    print("🔐 Connexion...")
    token = login()
    print("✅ Connecté\n")
    print(f"{'#':<4} {'Question':<50} {'Résultat':<8} SQL généré")
    print("─" * 120)

    ok_count = 0
    for i, item in enumerate(QUESTIONS, 1):
        q   = item["question"]
        exp = item["expected"]
        sql, ok = test_question(token, q, exp)
        status = "✅" if ok else "❌"
        if ok:
            ok_count += 1
        print(f"{i:<4} {q:<50} {status:<8} {sql}")
        time.sleep(1)  # petite pause entre les requêtes

    total = len(QUESTIONS)
    print("\n" + "─" * 120)
    print(f"RÉSULTAT : {ok_count}/{total} correct ({round(ok_count/total*100)}%)")

if __name__ == "__main__":
    main()

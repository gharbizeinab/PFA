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
    # patients → medecin ou staff
    {"question": "List all patients",                          "expected": "SELECT * FROM patients",              "role": "docteur"},
    {"question": "Show first and last names of all patients",  "expected": "SELECT first_name, last_name FROM patients", "role": "docteur"},
    {"question": "Find all female patients",                   "expected": "SELECT * FROM patients WHERE gender", "role": "staff"},
    {"question": "Find all male patients",                     "expected": "SELECT * FROM patients WHERE gender", "role": "staff"},
    {"question": "Show patients older than 70",                "expected": "WHERE age",                           "role": "docteur"},
    {"question": "Show patients younger than 50",              "expected": "WHERE age",                           "role": "docteur"},
    {"question": "Count total number of patients",             "expected": "SELECT COUNT(*)",                     "role": "staff"},
    {"question": "Find the oldest patient",                    "expected": "MAX(age)",                            "role": "docteur"},
    {"question": "Find the youngest patient",                  "expected": "MIN(age)",                            "role": "docteur"},
    {"question": "Show average patient age",                   "expected": "AVG(age)",                            "role": "docteur"},
    # services → admin, medecin, staff
    {"question": "List all services",                          "expected": "SELECT * FROM services",              "role": "admin"},
    {"question": "Show all service names",                     "expected": "SELECT service_name FROM services",   "role": "admin"},
    {"question": "Count total services",                       "expected": "SELECT COUNT(*)",                     "role": "admin"},
    # medical_staff → admin, medecin
    {"question": "List all medical staff",                     "expected": "SELECT * FROM medical_staff",         "role": "admin"},
    {"question": "Count total staff members",                  "expected": "SELECT COUNT(*)",                     "role": "admin"},
    # consultations → medecin, staff
    {"question": "List all consultations",                     "expected": "SELECT * FROM consultations",         "role": "docteur"},
    {"question": "Count total consultations",                  "expected": "SELECT COUNT(*)",                     "role": "docteur"},
    # medical_records → medecin uniquement
    {"question": "Show all medical records",                   "expected": "SELECT * FROM medical_records",       "role": "docteur"},
    # agrégats patients
    {"question": "Show average age by gender",                 "expected": "AVG(age)",                            "role": "docteur"},
    {"question": "Show patients sorted by age descending",     "expected": "ORDER BY age",                        "role": "docteur"},
    {"question": "Show staff sorted alphabetically",           "expected": "ORDER BY name_staff",                 "role": "admin"},
    {"question": "Find number of female patients",             "expected": "COUNT(*)",                            "role": "staff"},
    {"question": "Find number of male patients",               "expected": "COUNT(*)",                            "role": "staff"},
    {"question": "Count patients by blood group",              "expected": "GROUP BY blood_group",                "role": "staff"},
    {"question": "Show all consultations with patient names",  "expected": "JOIN patients",                       "role": "docteur"},
]

CREDENTIALS = {
    "admin":   {"username": "admin",   "password": "admin123"},
    "docteur": {"username": "docteur", "password": "doc123"},
    "staff":   {"username": "staff",   "password": "staff123"},
}

_token_cache = {}

def login(role="admin"):
    if role not in _token_cache:
        creds = CREDENTIALS[role]
        r = requests.post(f"{API}/api/auth/login", json=creds)
        _token_cache[role] = r.json()["token"]
    return _token_cache[role]

def test_question(token, question, expected_keyword):
    for attempt in range(3):  # 3 tentatives si Flask redémarre
        try:
            r = requests.post(
                f"{API}/api/chat/message",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json={"message": question},
                timeout=120
            )
            data = r.json()
            sql = data.get("sql", "") or ""
            ok  = expected_keyword.upper() in sql.upper()
            return sql, ok
        except Exception as e:
            if attempt < 2:
                time.sleep(3)  # attendre que Flask redémarre
            else:
                return f"ERREUR: {e}", False

def main():
    print("🔐 Connexion (admin / docteur / staff)...")
    login("admin"); login("docteur"); login("staff")
    print("✅ Connecté\n")
    print(f"{'#':<4} {'Question':<50} {'Rôle':<8} {'Résultat':<8} SQL généré")
    print("─" * 120)

    ok_count = 0
    for i, item in enumerate(QUESTIONS, 1):
        q     = item["question"]
        exp   = item["expected"]
        role  = item.get("role", "admin")
        token = login(role)
        sql, ok = test_question(token, q, exp)
        status = "✅" if ok else "❌"
        if ok:
            ok_count += 1
        print(f"{i:<4} {q:<50} {role:<8} {status:<8} {sql}")
        time.sleep(1)  # petite pause entre les requêtes

    total = len(QUESTIONS)
    print("\n" + "─" * 120)
    print(f"RÉSULTAT : {ok_count}/{total} correct ({round(ok_count/total*100)}%)")

if __name__ == "__main__":
    main()

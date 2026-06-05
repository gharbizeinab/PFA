# Champs obligatoires par table pour un INSERT
REQUIRED_FIELDS = {
    "patients":        ["first_name", "last_name"],
    "consultations":   ["id_patient", "symptoms"],
    "appointments":    ["id_patient", "appointment_date"],
    "medical_staff":   ["name_staff", "speciality"],
    "services":        ["service_name"],
    "medical_records": ["id_patient"],
}


class FieldValidator:
    def get_missing(self, table: str, attributes: dict, intent: str) -> list:
        if intent != 'INSERT':
            return []
        required = REQUIRED_FIELDS.get(table, [])
        return [f for f in required if not attributes.get(f)]


field_validator = FieldValidator()

PERMISSIONS = {
    'admin': {
        'users':           ['SELECT','INSERT','UPDATE'],
        'medical_staff':   ['SELECT','INSERT','UPDATE'],
        'services':        ['SELECT','INSERT','UPDATE'],
        'patients':        ['SELECT','INSERT','UPDATE'],
        'appointments':    ['SELECT','INSERT','UPDATE'],
        'consultations':   ['SELECT'],
        'medical_records': ['SELECT'],
        'ai_diagnosis':    ['SELECT'],
        'audit_logs':      ['SELECT'],
        'notifications':   ['SELECT','INSERT'],
    },
    'medecin': {
        'patients':        ['SELECT','INSERT','UPDATE'],
        'consultations':   ['SELECT','INSERT','UPDATE'],
        'medical_records': ['SELECT','INSERT','UPDATE'],
        'ai_diagnosis':    ['SELECT'],
        'appointments':    ['SELECT','INSERT','UPDATE'],
        'medical_staff':   ['SELECT'],
        'services':        ['SELECT'],
        'notifications':   ['SELECT','INSERT'],
    },
    'staff': {
        'patients':     ['SELECT','INSERT','UPDATE'],
        'appointments': ['SELECT','INSERT','UPDATE'],
        'consultations':['SELECT'],
        'services':     ['SELECT'],
        'notifications':['SELECT','INSERT'],
    }
}

def check_permission(role, table, action):
    return action.upper() in PERMISSIONS.get(role, {}).get(table.lower(), [])

def get_allowed_tables(role):
    return list(PERMISSIONS.get(role, {}).keys())

def role_required(*roles):
    """Décorateur : restreint une route aux rôles autorisés.
    Usage: @role_required('admin', 'medecin')"""
    from functools import wraps
    from flask_jwt_extended import jwt_required, get_jwt
    from flask import jsonify
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            role = get_jwt().get('role')
            if role not in roles:
                return jsonify({'error': 'Accès refusé', 'role': role, 'requis': list(roles)}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
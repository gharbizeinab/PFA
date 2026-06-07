PERMISSIONS = {
    'admin': {
        'users':         ['SELECT', 'INSERT', 'UPDATE'],
        'medical_staff': ['SELECT', 'INSERT', 'UPDATE'],
        'services':      ['SELECT', 'INSERT', 'UPDATE'],
        'audit_logs':    ['SELECT'],
        'notifications': ['SELECT'],
    },
    'intern': {
        'patients':        ['SELECT'],
        'consultations':   ['SELECT', 'INSERT', 'UPDATE'],
        'medical_records': ['SELECT', 'INSERT', 'UPDATE'],
        'ai_diagnosis':    ['SELECT'],
        'appointments':    ['SELECT'],
        'medical_staff':   ['SELECT'],
        'services':        ['SELECT'],
        'notifications':   ['SELECT'],
    },
    'staff': {
        'patients':      ['SELECT', 'INSERT', 'UPDATE'],
        'appointments':  ['SELECT', 'INSERT', 'UPDATE'],
        'consultations': ['SELECT'],
        'medical_staff': ['SELECT'],
        'users':         ['SELECT'],
        'services':      ['SELECT'],
        'notifications': ['SELECT'],
    },
}

def check_permission(role, table, action):
    return action.upper() in PERMISSIONS.get(role, {}).get(table.lower(), [])

def get_allowed_tables(role):
    return list(PERMISSIONS.get(role, {}).keys())

def role_required(*roles):
    """Decorator: restricts a route to the given roles.
    Usage: @role_required('admin', 'intern')"""
    from functools import wraps
    from flask_jwt_extended import jwt_required, get_jwt
    from flask import jsonify
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            role = get_jwt().get('role')
            if role not in roles:
                return jsonify({'error': 'Access denied', 'role': role, 'required': list(roles)}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
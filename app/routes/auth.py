from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt

auth_bp = Blueprint('auth', __name__)

# Utilisateurs de démo — dans un vrai projet : stockés en base avec bcrypt
DEMO_USERS = {
    'admin':   {'password': 'admin123',  'role': 'admin',   'id': 1},
    'docteur': {'password': 'doc123',    'role': 'medecin', 'id': 2},
    'staff':   {'password': 'staff123',  'role': 'staff',   'id': 3},
}

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON attendu'}), 400

    username = data.get('username', '')
    password = data.get('password', '')

    user = DEMO_USERS.get(username)
    if not user or user['password'] != password:
        return jsonify({'error': 'Identifiants incorrects'}), 401

    token = create_access_token(
        identity=username,
        additional_claims={'role': user['role'], 'user_id': user['id']}
    )
    return jsonify({'token': token, 'username': username, 'role': user['role']})

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def who_am_i():
    # Route protégée : nécessite le header Authorization: Bearer TOKEN
    claims = get_jwt()
    return jsonify({'username': claims.get('sub'), 'role': claims.get('role')})
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from sqlalchemy import text
from .. import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body expected'}), 400

    email    = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    row = db.session.execute(
        text("""
            SELECT id_user, first_name, last_name, email, role,
                   password_hash, department, avatar_initials
            FROM users
            WHERE email = :email AND password_hash IS NOT NULL
        """),
        {'email': email}
    ).fetchone()

    if not row:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not bcrypt.checkpw(password.encode(), row.password_hash.encode()):
        return jsonify({'error': 'Invalid credentials'}), 401

    full_name = f"{row.first_name} {row.last_name}"

    token = create_access_token(
        identity=row.email,
        additional_claims={
            'role':             row.role,
            'user_id':          row.id_user,
            'full_name':        full_name,
            'department':       row.department or '',
            'avatar_initials':  row.avatar_initials or '',
        }
    )

    return jsonify({
        'token':            token,
        'user_id':          row.id_user,
        'email':            row.email,
        'role':             row.role,
        'full_name':        full_name,
        'department':       row.department or '',
        'avatar_initials':  row.avatar_initials or '',
    })


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def who_am_i():
    claims = get_jwt()
    return jsonify({
        'email':           claims.get('sub'),
        'role':            claims.get('role'),
        'user_id':         claims.get('user_id'),
        'full_name':       claims.get('full_name'),
        'department':      claims.get('department'),
        'avatar_initials': claims.get('avatar_initials'),
    })

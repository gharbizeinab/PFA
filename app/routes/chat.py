from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from ..ai.pipeline import pipeline
from ..ai.sql_gen import sql_generator
from ..auth.rbac import check_permission, get_allowed_tables
from ..memory.conversation import ConversationMemory
from ..services.sql_executor import sql_executor
from ..services.response_gen import response_generator
from ..validators.sql_validator import sql_validator
from .. import db
from sqlalchemy import text
from datetime import date
import time, uuid

MEDICAL_ROLES = {'intern', 'staff'}

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST'])
@jwt_required()
def send_message():
    t0   = time.time()
    data = request.get_json()
    msg  = data.get('message', '').strip()
    sid  = data.get('session_id') or str(uuid.uuid4())

    if not msg:
        return jsonify({'error': 'Message cannot be empty'}), 400

    claims  = get_jwt()
    role    = claims.get('role')
    user_id = claims.get('user_id')
    mem     = ConversationMemory(current_app.redis_client)
    history = mem.get_history(sid)

    # ── 1. Resume pending multi-turn intent if any ──
    pending = mem.get_pending(sid)
    if pending:
        intent = pipeline.run(msg, history, pending_context=pending)
    else:
        intent = pipeline.run(msg, history)

    # ── 2. Conversational question — return directly ──
    table  = intent.get('table')
    action = intent.get('intent', 'SELECT')

    if action == 'QUESTION' and not pending:
        q = intent.get('clarification_question') or \
            "I'm a medical AI assistant. Ask me anything about patients, consultations, or appointments."
        mem.add_message(sid, 'user', msg)
        mem.add_message(sid, 'assistant', q)
        return jsonify({'response': q, 'type': 'question'})

    # ── 3. RBAC check ──
    if table:
        if not check_permission(role, table, action):
            mem.add_message(sid, 'user', msg)
            resp = (f"Access denied. Your role ({role}) does not have permission "
                    f"to perform {action} on {table}.")
            mem.add_message(sid, 'assistant', resp)
            return jsonify({'response': resp, 'type': 'access_denied'}), 403

    # ── 4. Missing fields — ask a clarifying question ──
    if intent.get('needs_clarification') and intent.get('missing_fields'):
        mem.save_pending(sid, intent)
        q = intent.get('clarification_question', 'Could you please clarify?')
        mem.add_message(sid, 'user', msg)
        mem.add_message(sid, 'assistant', q)
        return jsonify({'response': q, 'type': 'question', 'missing': intent.get('missing_fields', [])})

    # ── 5a. Contextual injection for appointments (medical roles) ──
    if table == 'appointments' and role in MEDICAL_ROLES:
        staff_rows = db.session.execute(
            text("SELECT id_staff FROM medical_staff WHERE id_user = :uid"),
            {'uid': user_id}
        ).fetchall()
        staff_ids = [r.id_staff for r in staff_rows]
        if staff_ids:
            intent['_staff_ids'] = staff_ids
            intent['_today']     = date.today().isoformat()

    # ── 5. Generate SQL ──
    sql_res = sql_generator.generate(intent, user_id)
    gen_sql = sql_res['sql']
    params  = sql_res['params']

    # ── 6. Validate SQL ──
    valid = sql_validator.validate(gen_sql, get_allowed_tables(role), action)
    if not valid['valid']:
        return jsonify({'response': f"Query rejected: {valid['error']}", 'type': 'error'})

    # ── 7. Execute ──
    db_res = sql_executor.execute(gen_sql, params)

    # ── 8. Generate natural-language response via Llama ──
    resp = response_generator.generate(msg, intent, db_res)

    mem.add_message(sid, 'user', msg)
    mem.add_message(sid, 'assistant', resp)
    mem.clear_pending(sid)

    return jsonify({
        'response':   resp,
        'data':       db_res['data'][:10],
        'sql':        gen_sql,
        'intent':     action,
        'table':      table,
        'session_id': sid,
        'latency_ms': int((time.time() - t0) * 1000)
    })

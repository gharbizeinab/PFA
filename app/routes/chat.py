from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from ..ai.pipeline import pipeline
from ..ai.sql_gen import sql_generator
from ..auth.rbac import check_permission, get_allowed_tables
from ..memory.conversation import ConversationMemory
from ..services.sql_executor import sql_executor
from ..validators.sql_validator import sql_validator
import time, uuid

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST'])
@jwt_required()
def send_message():
    t0 = time.time()
    data = request.get_json()
    msg = data.get('message','').strip()
    sid = data.get('session_id') or str(uuid.uuid4())

    if not msg:
        return jsonify({'error':'Message vide'}), 400

    claims  = get_jwt()
    role    = claims.get('role')
    user_id = claims.get('user_id')
    mem     = ConversationMemory(current_app.redis_client)
    history = mem.get_history(sid)

    # ── 1. Vérifier si intention en attente (multi-tour) ──
    pending = mem.get_pending(sid)
    if pending:
        intent = pipeline.run(msg, history, pending_context=pending)
    else:
        intent = pipeline.run(msg, history)

    # ── 2. Réponse directe si question conversationnelle ──
    table  = intent.get('table')
    action = intent.get('intent','SELECT')

    if action == 'QUESTION' and not pending:
        q = intent.get('clarification_question') or "Je suis un assistant médical. Posez-moi une question sur les patients, consultations ou rendez-vous."
        mem.add_message(sid, 'user', msg)
        mem.add_message(sid, 'assistant', q)
        return jsonify({'response': q, 'type': 'question'})

    # ── 3. Vérifier RBAC ──

    if table:
        if not check_permission(role, table, action):
            mem.add_message(sid, 'user', msg)
            resp = f"Accès refusé. Votre rôle ({role}) ne permet pas d'effectuer {action} sur {table}."
            mem.add_message(sid, 'assistant', resp)
            return jsonify({'response':resp, 'type':'access_denied'}), 403

    # ── 4. Infos manquantes → poser une question ──
    if intent.get('needs_clarification') and intent.get('missing_fields'):
        mem.save_pending(sid, intent)
        q = intent.get('clarification_question', 'Pouvez-vous préciser ?')
        mem.add_message(sid, 'user', msg)
        mem.add_message(sid, 'assistant', q)
        return jsonify({'response':q, 'type':'question', 'missing':intent.get('missing_fields',[])})

    # ── 4. Générer SQL ──
    sql_res = sql_generator.generate(intent, user_id)
    gen_sql = sql_res['sql']; params = sql_res['params']

    # ── 5. Valider SQL ──
    valid = sql_validator.validate(gen_sql, get_allowed_tables(role), action)
    if not valid['valid']:
        return jsonify({'response':f"Requête refusée : {valid['error']}", 'type':'error'})

    # ── 6. Exécuter ──
    db_res = sql_executor.execute(gen_sql, params)

    # ── 7. Formater la réponse ──
    if not db_res['ok']:
        resp = f"Erreur : {db_res.get('error', '?')}"
    elif action == 'SELECT':
        n = len(db_res['data'])
        resp = f"{n} résultat(s) trouvé(s)." if n > 0 else "Aucun résultat."
    else:
        resp = "Opération effectuée avec succès."

    mem.add_message(sid, 'user', msg)
    mem.add_message(sid, 'assistant', resp)
    mem.clear_pending(sid)

    return jsonify({
        'response': resp,
        'data': db_res['data'][:10],
        'sql': gen_sql, 'intent': action, 'table': table,
        'session_id': sid,
        'latency_ms': int((time.time()-t0)*1000)
    })
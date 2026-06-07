from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import text
from datetime import date, timedelta, datetime
from .. import db

dashboard_bp = Blueprint('dashboard', __name__)


def _row_to_dict(row) -> dict:
    return dict(row._mapping)


def _fix_status(appts: list, today_iso: str, default_date: str = '') -> list:
    """Auto-correct appointment statuses based on current date/time.

    Any appointment whose date+time is in the past and is still 'scheduled'
    is logically impossible — mark it 'completed' in the response (DB unchanged).
    Pass default_date when the rows don't carry a date field (e.g. today-only queries).
    """
    now_time_str = datetime.now().strftime('%H:%M')

    for appt in appts:
        if appt.get('status') != 'scheduled':
            continue
        appt_date = str(appt.get('appointment_date') or appt.get('date') or default_date)
        appt_time = str(appt.get('appointment_time') or appt.get('time') or '')[:5]
        if appt_date < today_iso or (appt_date == today_iso and appt_time < now_time_str):
            appt['status'] = 'completed'
    return appts


@dashboard_bp.route('', methods=['GET'])
@jwt_required()
def get_dashboard():
    claims   = get_jwt()
    user_id  = claims.get('user_id')
    role     = claims.get('role')
    today    = date.today()
    week_end = today + timedelta(days=6)

    # ── Resolve staff IDs for the logged-in user ────────────────────────────
    staff_rows = db.session.execute(
        text("SELECT id_staff, name_staff, speciality FROM medical_staff WHERE id_user = :uid"),
        {'uid': user_id}
    ).fetchall()
    staff_ids   = [r.id_staff for r in staff_rows]
    staff_name  = staff_rows[0].name_staff  if staff_rows else claims.get('full_name', '')
    speciality  = staff_rows[0].speciality  if staff_rows else ''

    if not staff_ids:
        return jsonify({'today': [], 'week': [], 'consultations': [],
                        'kpi': {}, 'staff_name': staff_name, 'speciality': speciality})

    # Build IN clause safely
    placeholders = ', '.join([f':sid{i}' for i in range(len(staff_ids))])
    sid_params   = {f'sid{i}': sid for i, sid in enumerate(staff_ids)}

    # ── KPIs ──────────────────────────────────────────────────────────────────
    kpi_row = db.session.execute(text(f"""
        SELECT
            COUNT(*) FILTER (WHERE appointment_date = :today)                           AS today_count,
            COUNT(*) FILTER (WHERE appointment_date BETWEEN :today AND :week_end)       AS week_count,
            COUNT(*) FILTER (WHERE status = 'scheduled' AND appointment_date >= :today) AS upcoming_count,
            COUNT(*) FILTER (WHERE status = 'completed')                                AS completed_count
        FROM appointments
        WHERE id_staff IN ({placeholders})
    """), {'today': today, 'week_end': week_end, **sid_params}).fetchone()

    kpi = {
        'today_count':     kpi_row.today_count,
        'week_count':      kpi_row.week_count,
        'upcoming_count':  kpi_row.upcoming_count,
        'completed_count': kpi_row.completed_count,
    }

    # ── Today's appointments ─────────────────────────────────────────────────
    today_rows = db.session.execute(text(f"""
        SELECT
            a.id_appointment,
            a.appointment_time  AS time,
            a.reason,
            a.status,
            p.first_name || ' ' || p.last_name AS patient_name,
            p.age,
            p.gender,
            p.id_patient
        FROM appointments a
        JOIN patients p ON a.id_patient = p.id_patient
        WHERE a.id_staff IN ({placeholders}) AND a.appointment_date = :today
        ORDER BY a.appointment_time
    """), {'today': today, **sid_params}).fetchall()

    today_appts = _fix_status([_row_to_dict(r) for r in today_rows], today.isoformat(), default_date=today.isoformat())

    # ── This week's appointments (grouped by day) ────────────────────────────
    week_rows = db.session.execute(text(f"""
        SELECT
            a.appointment_date::text AS date,
            a.appointment_time       AS time,
            a.reason,
            a.status,
            p.first_name || ' ' || p.last_name AS patient_name,
            p.age,
            p.gender,
            p.id_patient
        FROM appointments a
        JOIN patients p ON a.id_patient = p.id_patient
        WHERE a.id_staff IN ({placeholders})
          AND a.appointment_date BETWEEN :today AND :week_end
        ORDER BY a.appointment_date, a.appointment_time
    """), {'today': today, 'week_end': week_end, **sid_params}).fetchall()

    week_appts = _fix_status([_row_to_dict(r) for r in week_rows], today.isoformat())

    # ── Recent consultations ──────────────────────────────────────────────────
    consult_rows = db.session.execute(text(f"""
        SELECT
            c.consultation_date::text AS date,
            c.diagnosis,
            c.status,
            c.symptoms,
            p.first_name || ' ' || p.last_name AS patient_name,
            p.age,
            p.gender,
            p.id_patient
        FROM consultations c
        JOIN patients p ON c.id_patient = p.id_patient
        WHERE c.id_staff IN ({placeholders})
        ORDER BY c.consultation_date DESC
        LIMIT 8
    """), {**sid_params}).fetchall()

    consultations = [_row_to_dict(r) for r in consult_rows]

    return jsonify({
        'staff_name':   staff_name,
        'speciality':   speciality,
        'today_date':   today.isoformat(),
        'kpi':          kpi,
        'today':        today_appts,
        'week':         week_appts,
        'consultations': consultations,
    })


@dashboard_bp.route('/appointments', methods=['GET'])
@jwt_required()
def get_appointments_list():
    """Full appointments list for the appointments page."""
    claims  = get_jwt()
    user_id = claims.get('user_id')
    role    = claims.get('role')
    today   = date.today()

    if role == 'admin':
        rows = db.session.execute(text("""
            SELECT
                a.id_appointment,
                a.appointment_date::text  AS appointment_date,
                a.appointment_time::text  AS appointment_time,
                a.reason,
                a.status,
                p.first_name || ' ' || p.last_name AS patient_name,
                p.age,
                p.gender,
                s.name_staff  AS doctor_name,
                s.speciality  AS department
            FROM appointments a
            JOIN patients      p ON a.id_patient = p.id_patient
            JOIN medical_staff s ON a.id_staff   = s.id_staff
            ORDER BY a.appointment_date DESC, a.appointment_time
        """)).fetchall()
    else:
        staff_rows = db.session.execute(
            text("SELECT id_staff FROM medical_staff WHERE id_user = :uid"),
            {'uid': user_id}
        ).fetchall()
        staff_ids = [r.id_staff for r in staff_rows]

        if not staff_ids:
            return jsonify([])

        placeholders = ', '.join([f':sid{i}' for i in range(len(staff_ids))])
        sid_params   = {f'sid{i}': sid for i, sid in enumerate(staff_ids)}

        rows = db.session.execute(text(f"""
            SELECT
                a.id_appointment,
                a.appointment_date::text  AS appointment_date,
                a.appointment_time::text  AS appointment_time,
                a.reason,
                a.status,
                p.first_name || ' ' || p.last_name AS patient_name,
                p.age,
                p.gender,
                s.name_staff  AS doctor_name,
                s.speciality  AS department
            FROM appointments a
            JOIN patients      p ON a.id_patient = p.id_patient
            JOIN medical_staff s ON a.id_staff   = s.id_staff
            WHERE a.id_staff IN ({placeholders})
            ORDER BY a.appointment_date DESC, a.appointment_time
        """), sid_params).fetchall()

    result = _fix_status([_row_to_dict(r) for r in rows], today.isoformat())
    return jsonify(result)


@dashboard_bp.route('/clinic', methods=['GET'])
@jwt_required()
def get_clinic_dashboard():
    """Clinic-wide statistics dashboard for admin and staff roles."""
    today    = date.today()
    week_end = today + timedelta(days=6)

    # ── Global KPIs ───────────────────────────────────────────────────────────
    total_appointments = db.session.execute(
        text("SELECT COUNT(*) FROM appointments")
    ).scalar()

    today_appointments = db.session.execute(
        text("SELECT COUNT(*) FROM appointments WHERE appointment_date = :t"),
        {'t': today}
    ).scalar()

    week_appointments = db.session.execute(
        text("SELECT COUNT(*) FROM appointments WHERE appointment_date BETWEEN :t AND :we"),
        {'t': today, 'we': week_end}
    ).scalar()

    total_patients = db.session.execute(
        text("SELECT COUNT(*) FROM patients")
    ).scalar()

    total_doctors = db.session.execute(
        text("SELECT COUNT(*) FROM medical_staff")
    ).scalar()

    total_consultations = db.session.execute(
        text("SELECT COUNT(*) FROM consultations")
    ).scalar()

    # ── Appointments by status ────────────────────────────────────────────────
    status_rows = db.session.execute(
        text("SELECT status, COUNT(*) AS cnt FROM appointments GROUP BY status")
    ).fetchall()
    by_status = {r.status: r.cnt for r in status_rows}

    # ── Appointments by service (top 6) ───────────────────────────────────────
    service_rows = db.session.execute(text("""
        SELECT s.service_name, COUNT(*) AS cnt
        FROM appointments a
        JOIN medical_staff ms ON a.id_staff   = ms.id_staff
        JOIN services      s  ON ms.id_service = s.id_service
        GROUP BY s.service_name
        ORDER BY cnt DESC
        LIMIT 6
    """)).fetchall()
    by_service = [{'service': r.service_name, 'count': r.cnt} for r in service_rows]

    # ── Consultations by status ───────────────────────────────────────────────
    consult_rows = db.session.execute(
        text("SELECT status, COUNT(*) AS cnt FROM consultations GROUP BY status")
    ).fetchall()
    consult_by_status = {r.status: r.cnt for r in consult_rows}

    # ── Recently registered patients (last 8) ─────────────────────────────────
    recent_rows = db.session.execute(text("""
        SELECT first_name, last_name, gender, age, blood_group
        FROM patients
        ORDER BY id_patient DESC
        LIMIT 8
    """)).fetchall()
    recent_patients = [
        {
            'name':        f"{r.first_name} {r.last_name}",
            'gender':      r.gender or '—',
            'age':         r.age,
            'blood_group': r.blood_group or '—',
        }
        for r in recent_rows
    ]

    # ── Top 5 today's appointments with patient info ──────────────────────────
    today_rows = db.session.execute(text("""
        SELECT
            a.appointment_time  AS time,
            a.reason,
            a.status,
            p.first_name || ' ' || p.last_name AS patient_name,
            p.age,
            p.gender,
            ms.name_staff  AS doctor_name,
            s.service_name AS service
        FROM appointments a
        JOIN patients      p  ON a.id_patient = p.id_patient
        JOIN medical_staff ms ON a.id_staff   = ms.id_staff
        JOIN services      s  ON ms.id_service = s.id_service
        WHERE a.appointment_date = :today
        ORDER BY a.appointment_time
        LIMIT 10
    """), {'today': today}).fetchall()
    today_list = [_row_to_dict(r) for r in today_rows]

    return jsonify({
        'today_date':          today.isoformat(),
        'kpi': {
            'total_appointments': total_appointments,
            'today_appointments': today_appointments,
            'week_appointments':  week_appointments,
            'total_patients':     total_patients,
            'total_doctors':      total_doctors,
            'total_consultations': total_consultations,
        },
        'by_status':           by_status,
        'by_service':          by_service,
        'consult_by_status':   consult_by_status,
        'recent_patients':     recent_patients,
        'today_list':          today_list,
    })

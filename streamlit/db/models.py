from db.supabase_client import get_supabase


def get_doctor_by_token(token):
    sb = get_supabase()
    if not sb:
        return None
    try:
        result = sb.table('doctors').select('*').eq('id', token).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def get_doctor_by_email(email):
    sb = get_supabase()
    if not sb:
        return None
    try:
        result = sb.table('doctors').select('*').eq('email', email.lower().strip()).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def create_doctor(name, email):
    sb = get_supabase()
    if not sb:
        return None
    try:
        result = sb.table('doctors').insert({
            'name': name.strip(),
            'email': email.lower().strip(),
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def create_session(doctor_id, symptom, gender, age, preset):
    sb = get_supabase()
    if not sb or not doctor_id:
        return None
    try:
        result = sb.table('sessions').insert({
            'doctor_id': doctor_id,
            'symptom_input': symptom,
            'gender_input': gender,
            'age_input': age,
            'preset_used': preset,
        }).execute()
        return result.data[0]['id'] if result.data else None
    except Exception:
        return None


def log_question(session_id, order, q_type, question_text, answer, comment,
                 pool_after, eliminated):
    sb = get_supabase()
    if not sb or not session_id:
        return
    try:
        sb.table('question_logs').insert({
            'session_id': session_id,
            'question_order': order,
            'question_type': q_type,
            'question_text': question_text,
            'answer': str(answer),
            'doctor_comment': comment if comment else None,
            'pool_after': pool_after,
            'eliminated_count': eliminated,
        }).execute()
    except Exception:
        pass


def log_results(session_id, result_rows):
    sb = get_supabase()
    if not sb or not session_id or not result_rows:
        return
    try:
        sb.table('condition_results').insert(result_rows).execute()
    except Exception:
        pass


def log_evaluation(session_id, intended_rank, comment):
    sb = get_supabase()
    if not sb or not session_id:
        return
    try:
        sb.table('evaluations').insert({
            'session_id': session_id,
            'intended_diagnosis_rank': intended_rank,
            'overall_comment': comment,
        }).execute()
    except Exception:
        pass

import streamlit as st


def check_auth():
    from db.supabase_client import get_supabase

    if get_supabase() is None:
        if 'doctor' not in st.session_state:
            st.session_state.doctor = {
                'id': 'local', 'name': 'Local User', 'email': '',
            }
        return True

    if 'doctor' in st.session_state:
        return True

    token = st.query_params.get("token")
    if token:
        from db.models import get_doctor_by_token
        doctor = get_doctor_by_token(token)
        if doctor:
            st.session_state.doctor = doctor
            return True

    return False


def render():
    if check_auth():
        st.session_state.page = 'intake'
        st.rerun()
        return

    st.markdown(
        """
        <div style="text-align: center; padding: 40px 0 20px 0;">
            <h1 style="margin-bottom: 4px; color: #0f172a;">
                Symptom Checker Engine
            </h1>
            <p style="color: #64748b; font-size: 1.05em; margin-top: 4px;">
                Please enter your details to begin
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("register_form"):
        name = st.text_input("Your Name", placeholder="Dr. Ahmed")
        email = st.text_input("Email", placeholder="ahmed@hospital.com")
        submitted = st.form_submit_button(
            "Continue", type="primary", use_container_width=True,
        )

    if submitted:
        if not name or not name.strip():
            st.error("Please enter your name.")
            return
        if not email or not email.strip() or '@' not in email:
            st.error("Please enter a valid email address.")
            return

        from db.models import get_doctor_by_email, create_doctor

        doctor = get_doctor_by_email(email)
        if doctor:
            st.session_state.doctor = doctor
            st.query_params["token"] = str(doctor['id'])
            st.session_state.page = 'intake'
            st.rerun()
        else:
            new_doctor = create_doctor(name.strip(), email.strip())
            if new_doctor:
                st.session_state.doctor = new_doctor
                st.query_params["token"] = str(new_doctor['id'])
                st.session_state.page = 'intake'
                st.rerun()
            else:
                st.error(
                    "Could not create account. "
                    "Please check the database connection."
                )

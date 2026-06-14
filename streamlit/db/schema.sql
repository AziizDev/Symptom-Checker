-- Run this in the Supabase SQL Editor to create all tables.

CREATE TABLE doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID REFERENCES doctors(id),
    symptom_input TEXT NOT NULL,
    gender_input TEXT NOT NULL,
    age_input INTEGER NOT NULL,
    preset_used TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE question_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    question_order INTEGER NOT NULL,
    question_type TEXT NOT NULL,
    question_text TEXT NOT NULL,
    answer TEXT NOT NULL,
    doctor_comment TEXT,
    pool_after INTEGER NOT NULL,
    eliminated_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE evaluations (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    intended_diagnosis_rank INTEGER NOT NULL CHECK (intended_diagnosis_rank BETWEEN 1 AND 5),
    overall_comment TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_doctor ON sessions(doctor_id);
CREATE INDEX idx_question_logs_session ON question_logs(session_id);
CREATE INDEX idx_evaluations_session ON evaluations(session_id);

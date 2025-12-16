from backend.models import engine, Session
from sqlmodel import Session as DbSession, select

with DbSession(engine) as db:
    sessions = db.exec(select(Session)).all()
    if not sessions:
        print('NO_SESSIONS')
    for s in sessions:
        print(s.id, s.slot_id, s.is_active, s.start_time, s.end_time)

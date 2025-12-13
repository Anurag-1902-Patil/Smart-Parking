from sqlmodel import Session as DbSession, select
from models import engine, Session

with DbSession(engine) as db:
    sid = "REAL_TEST_SESSION"
    session = db.exec(select(Session).where(Session.id == sid)).first()
    
    if session:
        print(f"Session '{sid}': Active={session.is_active}, EndTime={session.end_time}")
    else:
        print(f"Session '{sid}' NOT FOUND")

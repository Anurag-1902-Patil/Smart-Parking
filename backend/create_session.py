from sqlmodel import Session as DbSession, select
from models import engine, Slot, Session, create_db_and_tables
from datetime import datetime

create_db_and_tables()

with DbSession(engine) as db:
    # Cleanup
    db.exec(Session.__table__.delete())
    db.exec(Slot.__table__.delete())
    
    # Create Slot
    slot = Slot(id=1, status="reserved")
    
    # Create Session
    sid = "REAL_TEST_SESSION"
    session = Session(id=sid, token="debug_token", slot_id=1, start_time=datetime.now(), is_active=True)
    
    slot.session_id = sid
    
    db.add(session)
    db.add(slot)
    db.commit()
    
    print(f"SUCCESS: Created session '{sid}' for Slot 1")

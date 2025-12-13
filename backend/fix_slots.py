from sqlmodel import Session as DbSession, select
from models import engine, Slot

TOTAL_SLOTS = 4

with DbSession(engine) as db:
    print("Checking slots...")
    existing_slots = db.exec(select(Slot)).all()
    existing_ids = {s.id for s in existing_slots}
    
    print(f"Found {len(existing_ids)} slots: {existing_ids}")
    
    for i in range(1, TOTAL_SLOTS + 1):
        if i not in existing_ids:
            print(f"Creating missing slot {i}...")
            db.add(Slot(id=i, status="free"))
            
    db.commit()
    print("Done. Total slots should be 4.")

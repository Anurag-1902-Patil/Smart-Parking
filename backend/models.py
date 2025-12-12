from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine

class Slot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="free")  # free, reserved, occupied
    session_id: Optional[str] = Field(default=None)

class Session(SQLModel, table=True):
    id: str = Field(primary_key=True)
    token: str
    slot_id: int
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    is_active: bool = True

# Database Setup
sqlite_file_name = "parking.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

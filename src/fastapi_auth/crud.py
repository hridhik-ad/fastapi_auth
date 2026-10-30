# crud.py
from typing import TypeVar, Generic, Type
from sqlalchemy.orm import Session
from fastapi_auth.database import TeamDB, PlayerDB

ModelType = TypeVar("ModelType")

# 1. The Universal Robot
class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def save(self, db: Session, record: ModelType) -> ModelType:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_all(self, db: Session) -> list[ModelType]:
        return db.query(self.model).all()

   
        

# 2. The Specialized Robot (Inheritance)
class PlayerRepository(CRUDBase[PlayerDB]):
    def __init__(self):
        super().__init__(PlayerDB) # Tell parent to use PlayerDB

    def get_suspended_players(self, db: Session) -> list[PlayerDB]:
        # Custom SQL query
        return db.query(self.model).filter(self.model.is_suspended == True).all()

    def checker(self, db: Session, name) -> bool:
        return db.query(self.model).filter(self.model.name == name).all()
    
# 3. Instantiate the tools for the web routes

class TeamRepository(CRUDBase[TeamDB]):
    def __init__(self):
        super().__init__(TeamDB)

    def get_by_email(self, db: Session, email: str) -> TeamDB:
        # We query the DB specifically for this email
        
        value = db.query(self.model).filter(self.model.captain_email == email).first()
        return value


team_repo = TeamRepository()
player_repo = PlayerRepository()



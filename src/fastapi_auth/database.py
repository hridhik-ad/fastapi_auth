# database.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Create SQLite Engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./turfez.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 2. Session Factory
SessionLocal = sessionmaker(autoflush=False, bind=engine)

# 3. Base Blueprint
Base = declarative_base()

# 4. The Models (Vaults)
class TeamDB(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, index=True)
    captain_email = Column(String)

class PlayerDB(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_suspended = Column(Boolean, default=False)


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    
    # We NEVER save actual passwords. We save a scrambled "hash".
    hashed_password = Column(String, nullable=False)

    

# 5. Generate tables on hard drive
Base.metadata.create_all(bind=engine)


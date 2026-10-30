# main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

# Import our custom modules
from fastapi_auth.database import SessionLocal, TeamDB, PlayerDB, UserDB
from fastapi_auth.crud import team_repo, player_repo

from pwdlib import PasswordHash

import jwt
from fastapi.security import OAuth2PasswordRequestForm


from fastapi.security import OAuth2PasswordBearer



app = FastAPI()





# --- DEPENDENCIES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tells Swagger UI where to get the token (your login route)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# THE BOUNCER FUNCTION
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        # Read the wristband
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        
        # Look up the user
        user = db.query(UserDB).filter(UserDB.email == email).first()
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid Wristband")

# THE VIP ROOM (Your Protected Route)
@app.get("/allTeams")
def get_all_teams(
    db: Session = Depends(get_db), 
    current_user: UserDB = Depends(get_current_user) # The bouncer is assigned here!
):
    # If the code reaches here, the user is authenticated.
    teams = db.query(TeamDB).all()
    return teams




class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.addr_count = {}

    def __call__(self, request: Request):
        ip = request.client.host 
        if self.addr_count.get(ip, 0) >= self.limit:
            raise HTTPException(status_code=429, detail="Rate Limit Exceeded")
        self.addr_count[ip] = self.addr_count.get(ip, 0) + 1
        return True   


firewall = RateLimiter(limit=100) # Set high so you can test easily

# --- PYDANTIC MODELS (The Bouncers) ---
class TeamCreate(BaseModel):
    team_name: str
    captain_email: EmailStr

class PlayerCreate(BaseModel):
    name: str
    is_suspended: bool = False

class PlayerNameChecker(BaseModel):
    name: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str



# The tool that scrambles passwords

password_hash = PasswordHash.recommended()

# --- ROUTES ---

#register a new user

@app.get("/")
def root():
    return {"message": "Welcome to the FastAPI Auth System!"}


@app.post("/register", dependencies=[Depends(firewall)])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # 1. Scramble the password
    scrambled_password = password_hash.hash(user.password)
    
    # 2. Save to database
    new_user = UserDB(email=user.email, hashed_password=scrambled_password)
    db.add(new_user)
    db.commit()
    
    return {"message": "User created!"}

@app.get("/allUsers", dependencies=[Depends(firewall)])
def all_users(db: Session = Depends(get_db)):
    return db.query(UserDB).all()




## --- LOGIN & JWT ---
SECRET_KEY = "super_secret_key" # The stamp used to make the wristband

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Find user in database by email (Swagger uses 'username' for email)
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    
    # 2. Verify the password matches the scrambled hash
    if not user or not password_hash.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    
    # 3. Create the JWT (The VIP Wristband)
    wristband = jwt.encode({"sub": user.email}, SECRET_KEY, algorithm="HS256")
    
    # FastAPI requires this exact dictionary format for tokens
    return {"access_token": wristband, "token_type": "bearer"}









@app.post("/addTeams", dependencies=[Depends(firewall)])
def register_team(payload: TeamCreate, db: Session = Depends(get_db)):
    db_team = TeamDB(team_name=payload.team_name, captain_email=payload.captain_email)
    return team_repo.save(db, db_team)


@app.get("/teams/get_teamName", dependencies=[Depends(firewall)])
def teamName(email:str, db: Session = Depends(get_db)):

    check = team_repo.get_by_email(db, email = email)
    return check



@app.get("/allTeams")
def allTeams(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)  # <-- The Bouncer
    
    ):
    return team_repo.get_all(db)


#-- Player routes ---
@app.post("/addPlayers", dependencies=[Depends(firewall)])
def register_player(
    payload: PlayerCreate, 
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)  # <-- The Bouncer
):
    db_player = PlayerDB(name=payload.name, is_suspended=payload.is_suspended)
    return player_repo.save(db, db_player)


@app.get("/allPlayers", dependencies=[Depends(firewall)])
def allPlayers(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)  # <-- The Bouncer
               ):

    return player_repo.get_all(db)


@app.get("/player/name_checker", dependencies=[Depends(firewall)])
def check_player(
    name: str, 
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)  # <-- The Bouncer
    
    ):
    
    if player_repo.checker(db, name = name):
        return ("Exists")
    else: 
        return ("No data")


@app.get("/players/suspended")
def get_suspended(db: Session = Depends(get_db)):
    # This triggers your custom method!
    return player_repo.get_suspended_players(db)



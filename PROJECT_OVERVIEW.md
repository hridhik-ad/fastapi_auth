# FastAPI Auth Project Overview

## Purpose

This project is a small FastAPI backend for managing football teams and players. Authentication is planned but has not yet been implemented.

## Project Structure

```text
fastapi_auth/
├── pyproject.toml
├── requirements.txt
├── README.md
├── PROJECT_OVERVIEW.md
└── src/
    └── fastapi_auth/
        ├── __init__.py
        ├── crud.py
        ├── database.py
        └── main.py
```

## Technology Stack

- Python >= 3.12
- FastAPI
- SQLAlchemy 2.x
- SQLite
- Pydantic v2
- Uvicorn
- `uv` for package and environment management

## Current Database Configuration

File: `src/fastapi_auth/database.py`

- Database URL: `sqlite:///./turfez.db`
- SQLAlchemy engine uses `check_same_thread=False` for SQLite.
- `SessionLocal` creates database sessions.
- `Base` is the declarative SQLAlchemy base.
- Tables are currently created with `Base.metadata.create_all(bind=engine)`.
- Alembic migrations are not configured yet.

### Current Models

```python
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
```

## Current Pydantic Schemas

File: `src/fastapi_auth/main.py`

```python
class TeamCreate(BaseModel):
    team_name: str
    captain_email: EmailStr


class PlayerCreate(BaseModel):
    name: str
    is_suspended: bool = False


class PlayerNameChecker(BaseModel):
    name: str
```

`PlayerNameChecker` currently exists but is not used by any route.

## Database Dependency

The `get_db` dependency creates a SQLAlchemy session for each request and closes it afterward:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Current Request Rate Limiter

`RateLimiter` is a simple in-memory limiter keyed by client IP address.

```python
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
```

Current configuration:

```python
firewall = RateLimiter(limit=100)
```

Limitations:

- Counts requests for the lifetime of the process.
- Resets when the server restarts.
- Does not expire old entries.
- Is not suitable for multiple server workers.
- Should eventually be applied specifically to login attempts or replaced with Redis-backed limiting.

## Current API Routes

File: `src/fastapi_auth/main.py`

### Team Routes

```text
POST /addTeams
```

Creates a team using `TeamCreate`.

```text
GET /teams/get_teamName?email={email}
```

Finds one team by captain email.

```text
GET /allTeams
```

Returns all teams.

### Player Routes

```text
POST /addPlayers
```

Creates a player using `PlayerCreate`.

```text
GET /allPlayers
```

Returns all players.

```text
GET /player/name_checker?name={name}
```

Checks whether a player with the given name exists. Returns either `"Exists"` or `"No data"`.

```text
GET /players/suspended
```

Returns players where `is_suspended == True`.

## CRUD Layer

File: `src/fastapi_auth/crud.py`

### `CRUDBase`

Generic repository with:

```python
save(db, record)
get_all(db)
```

`save` adds, commits, refreshes, and returns a database record.

### `TeamRepository`

Uses `TeamDB` and provides:

```python
get_by_email(db, email)
```

Returns the first team whose `captain_email` matches the supplied email.

### `PlayerRepository`

Uses `PlayerDB` and provides:

```python
get_suspended_players(db)
checker(db, name)
```

`checker` currently returns the result of `.all()`, which is a list. It is used as a truthy existence check by the route.

## Important Current Gaps

- There is no user table.
- There is no password field or password hashing.
- There is no registration endpoint.
- There is no login endpoint.
- There is no JWT or session authentication.
- Existing routes are not protected by an authenticated-user dependency.
- `captain_email` is plain text and is not linked to a user record.
- `Base.metadata.create_all` is being used instead of migrations.
- There are no automated tests yet.
- There are no response schemas for database objects.
- Error handling and validation can be improved.
- The current `firewall` is not a production-ready rate limiter.

## Recommended Authentication Design

For an API consumed by a separate frontend or mobile client, use JWT access tokens.

### Recommended Dependencies

```bash
uv add pwdlib pyjwt python-multipart
```

### Recommended New User Model

Add a `UserDB` model to `database.py`:

```python
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
```

Use a user ID foreign key for team ownership rather than storing the captain email directly:

```python
captain_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

### Recommended Authentication Schemas

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
```

### Recommended Authentication Routes

```text
POST /auth/register
POST /auth/login
GET /auth/me
```

- `/auth/register` validates the email, hashes the password, and creates a user.
- `/auth/login` verifies the password and returns a short-lived access token.
- `/auth/me` returns the currently authenticated user.

### Recommended Authentication Helpers

Create a separate `auth.py` module containing:

- Password hashing and verification using `pwdlib`.
- JWT creation using `pyjwt`.
- `OAuth2PasswordBearer(tokenUrl="/auth/login")`.
- `get_current_user` dependency that decodes the token and loads the user.
- Environment-based configuration for `SECRET_KEY` and token expiry.

Example protected route:

```python
@app.get("/allTeams")
def all_teams(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return team_repo.get_all(db)
```

Never store plaintext passwords. Never hard-code the production JWT secret in source code.

## Suggested Implementation Order

1. Add `UserDB` and authentication schemas.
2. Add password hashing utilities.
3. Add registration and login routes.
4. Add JWT validation and `get_current_user`.
5. Protect team and player routes.
6. Link teams to users with `captain_id`.
7. Add Alembic migrations.
8. Add tests for registration, login, invalid passwords, expired tokens, and protected routes.
9. Replace the in-memory rate limiter with a production-ready solution.

## Development Commands

Run the API from the project root:

```bash
uv run uvicorn fastapi_auth.main:app --reload
```

The interactive API documentation should be available at:

```text
http://127.0.0.1:8000/docs
```

## Context for the Next LLM

When modifying this project:

- Preserve the existing FastAPI and SQLAlchemy structure unless a change is necessary.
- Keep authentication code separate from general CRUD code.
- Prefer small, testable functions.
- Use SQLAlchemy models for persistence and Pydantic models for request/response validation.
- Do not store plaintext passwords.
- Protect private routes with a reusable dependency instead of duplicating token logic.
- Be aware that the database currently uses SQLite and creates tables at import time.
- Check existing user changes before editing; do not overwrite unrelated work.

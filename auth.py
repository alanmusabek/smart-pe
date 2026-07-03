"""
auth.py — JWT authentication for Smart PE
Roles: student, teacher
Run: uvicorn main:app --reload --port 8000
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from feature_extractor import get_connection

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = "smart-pe-secret-key-change-in-production-2026"  # TODO: move to .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ── Schemas ─────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    student_id: Optional[int] = None
    role: str = "student"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    student_id: Optional[int] = None

class UserResponse(BaseModel):
    user_id: int
    email: str
    role: str
    student_id: Optional[int] = None

# ─ Helpers ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    
    # ✅ FIX: JWT standard requires 'sub' and custom IDs to be strings
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if "student_id" in to_encode and to_encode["student_id"] is not None:
        to_encode["student_id"] = str(to_encode["student_id"])
        
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency: extract and validate JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # ✅ FIX: Cast back to integers after decoding
        user_id: int = int(payload.get("sub"))
        role: str = payload.get("role")
        student_id_str = payload.get("student_id")
        student_id: Optional[int] = int(student_id_str) if student_id_str is not None else None
        
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"user_id": user_id, "role": role, "student_id": student_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_student(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return user

def get_current_teacher(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user

# ── Routes ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    if req.role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if req.role == "student" and not req.student_id:
        raise HTTPException(status_code=400, detail="student_id required for student role")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE email = %s", (req.email,))
    if cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=409, detail="Email already registered")

    if req.role == "student":
        cur.execute("SELECT student_id FROM students WHERE student_id = %s", (req.student_id,))
        if not cur.fetchone():
            cur.close(); conn.close()
            raise HTTPException(status_code=404, detail="Student not found in DB")

    password_hash = hash_password(req.password)
    cur.execute(
        """INSERT INTO users (email, password_hash, role, student_id, is_active)
           VALUES (%s, %s, %s, %s, %s) RETURNING user_id""",
        (req.email, password_hash, req.role, req.student_id, True)
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()

    token = create_access_token({
        "sub": user_id,
        "role": req.role,
        "student_id": req.student_id,
    })
    return TokenResponse(access_token=token, role=req.role, student_id=req.student_id)

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, password_hash, role, student_id FROM users WHERE email = %s", (req.email,))
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row or not verify_password(req.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, _, role, student_id = row
    token = create_access_token({"sub": user_id, "role": role, "student_id": student_id})
    return TokenResponse(access_token=token, role=role, student_id=student_id)

@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, email, role, student_id, is_active FROM users WHERE user_id = %s", (user["user_id"],))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(user_id=row[0], email=row[1], role=row[2], student_id=row[3])
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import AdminUser
from app.schemas.schemas import AdminRegisterRequest, AdminLoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: AdminRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = AdminUser(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token)

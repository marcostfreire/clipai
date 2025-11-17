"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserRead, Token
from ..services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from ..config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize OAuth
oauth = OAuth()

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Login and receive an access token."""
    # Find user by email (username field in OAuth2 form)
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login."""
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    redirect_uri = f"{settings.oauth_redirect_uri}/google"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            raise HTTPException(
                status_code=400, detail="Failed to get user info from Google"
            )

        email = user_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Check if user exists
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Create new user
            user = User(
                email=email,
                oauth_provider="google",
                oauth_id=user_info.get("sub"),
                full_name=user_info.get("name"),
                avatar_url=user_info.get("picture"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create access token
        access_token = create_access_token(data={"sub": user.email})

        # Redirect to frontend with token
        frontend_url = f"http://localhost:3000/auth/callback?token={access_token}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

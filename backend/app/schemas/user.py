from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Données pour créer un compte (inscription)."""
    email: EmailStr
    password: str
    full_name: str = ""


class UserLogin(BaseModel):
    """Données pour se connecter."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Données renvoyées à l'utilisateur (JAMAIS le mot de passe !)."""
    id: str
    email: str
    full_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Le token JWT renvoyé après une connexion réussie."""
    access_token: str
    token_type: str = "bearer"
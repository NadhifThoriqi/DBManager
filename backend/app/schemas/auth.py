from enum import StrEnum

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ──────────────────────────────────────────────

class TypeDB(StrEnum):
    SQLITE="sqlite"
    MYSQL="mysql"
    POSTGRESQL="postgresql"

class UserBase(BaseModel):
    user: str = Field(..., description="Username atau email pengguna")
    db: TypeDB = Field(..., description="Masukkan database yang ingin kamu akses ['sqlite', 'mysql', 'postgresql']")
    host: str
    port: int

class SignInRequest(UserBase):
    password: str = Field(..., description="Password pengguna untuk masuk")

class AuthMessageResponse(BaseModel):
    message: str

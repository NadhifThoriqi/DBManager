from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ..services import auth

router = APIRouter(prefix="/auth", tags=["Auth"])


# ──────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ──────────────────────────────────────────────

class UserBase(BaseModel):
    user: str = Field(..., description="Username atau email pengguna")
    db: Literal["sqlite", "mysql", "postgresql"] = Field(..., description="Masukkan database yang ingin kamu akses ['sqlite', 'mysql', 'postgresql']")


class SignInRequest(UserBase):
    password: str = Field(..., description="Password pengguna untuk masuk")


class SignUpRequest(UserBase):
    password: str = Field(..., description="Password pengguna baru")


class AuthMessageResponse(BaseModel):
    message: str


# ──────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ──────────────────────────────────────────────

@router.post(
    "/signin",
    response_model=Any,
    summary="User Sign In / Login",
    description="Melakukan autentikasi pengguna dan mengembalikan token atau mengatur session cookie.",
)
def sign_in(response: Response, body: SignInRequest) -> Any:
    try:
        # Menambahkan response jika service 'masuk' membutuhkan penanganan cookie
        result = auth.masuk(response, body)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/signup",
    response_model=AuthMessageResponse,
    summary="User Sign Up / Register",
    description="Mendaftarkan pengguna baru ke dalam sistem dengan username dan password.",
)
def sign_up(response: Response, body: SignUpRequest) -> AuthMessageResponse:
    try:
        # MEMPERBAIKI BUG: Mengubah 'masuk' menjadi 'daftar'
        result = auth.daftar(response, body)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/logout",
    response_model=AuthMessageResponse,
    summary="User Log Out",
    description="Menghapus session atau token autentikasi yang aktif dari sisi client.",
)
def log_out(response: Response) -> AuthMessageResponse:
    try:
        auth.keluar(response)
        return AuthMessageResponse(message="Berhasil keluar dari sistem.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
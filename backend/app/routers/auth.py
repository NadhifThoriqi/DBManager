from typing import Any

from fastapi import APIRouter, HTTPException, Response

from ..services import auth
from ..schemas.auth import (SignInRequest, 
                            AuthMessageResponse)

router = APIRouter(prefix="/auth", tags=["Backend - Auth"])


# ──────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ──────────────────────────────────────────────

@router.post(
    "/signin",
    response_model=Any,
    summary="User Sign In / Login",
    description="Melakukan autentikasi pengguna dan mengembalikan token atau mengatur session cookie.",
)
async def sign_in(response: Response, body: SignInRequest) -> Any:
    try:
        # Menambahkan response jika service 'masuk' membutuhkan penanganan cookie
        result =await auth.masuk(response, body)
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
async def log_out(response: Response) -> AuthMessageResponse:
    try:
        await auth.keluar(response)
        return AuthMessageResponse(message="Berhasil keluar dari sistem.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
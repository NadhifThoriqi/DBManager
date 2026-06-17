from fastapi import Response, HTTPException, Cookie
from typing import Any, Dict, Optional, cast, Union
from datetime import timedelta, datetime, timezone
from dotenv import load_dotenv

from ..api import auth

import jwt
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY tidak ditemukan di environment variables!")

ALGORITHM = "HS256"

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Membuat JWT access token.

    Data minimal biasanya:
    {
        "sub": user_id
    }
    """
    
    to_encode = data.copy()
    
    # Gunakan timezone-aware datetime agar lebih akurat dan aman
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Payload JWT
    to_encode.update({"exp": expire})
    
    # Encode menggunakan PyJWT
    encoded_jwt = jwt.encode(payload=to_encode, key=cast(str, SECRET_KEY), algorithm=ALGORITHM)
    return str(encoded_jwt)

def create_cookie(response: Response, body: Union[auth.SignUpRequest, auth.SignInRequest]) -> str:
    token_data: Dict[str, Any] = {
        "sub": body.user,
        "pw": body.password,
        "db": body.db,
        "type": "access"
    }

    access_token = create_access_token(data=token_data)

    # Simpan token ke Cookie (HTTPOnly untuk keamanan)
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True,      # JavaScript tidak bisa mengakses cookie
        max_age=2592000,    # 30 hari
        expires=2592000,
        samesite="lax",     # Proteksi dasar CSRF
        secure=False,       # Ubah ke True jika sudah HTTPS
        domain=None,        # biarkan None, jangan diisi manual
        path="/",           # ← wajib "/" agar berlaku di semua halaman
    )

    return "Login berhasil"

def get_cookie(access_token: Optional[str] = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Log in dulu yuk")
    try:
        # Decode kembali tokennya
        payload = jwt.decode(access_token, cast(str, SECRET_KEY), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token sudah kadaluwarsa, silakan login ulang")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token rusak atau tidak valid")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Gagal memproses token")
    
    token_id: str = payload.get("sub") or ""
    if not token_id:
        raise HTTPException(status_code=401, detail="Payload token tidak valid")


    token_type = payload.get("type")
    # Pastikan tipe token adalah untuk login/access, bukan reset_password
    if token_type != "access": # nosec
        raise HTTPException(status_code=401, detail="Tipe token tidak valid untuk login")

    return payload

def masuk(response: Response, body: auth.SignInRequest) -> Any:
    return create_cookie(response, body)

def daftar(response: Response, body: auth.SignUpRequest) -> Any: 
    return create_cookie(response, body)

def keluar(response: Response) -> str: 
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        # Pastikan path sama dengan set_cookie jika pernah diatur
    )
    return "Berhasil keluar"
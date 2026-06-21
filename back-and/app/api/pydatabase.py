"""
================
api/api_database.py
================
FastAPI APIRouter untuk operasi manajemen database (Create, Show, Delete).
Hanya berisi definisi endpoint dan request/response model.
Seluruh logika bisnis ada di services/pydatabase.py.

Endpoint:
    POST   /database/create/sqlite
    POST   /database/create/mysql
    POST   /database/create/postgresql
    GET    /database/show/sqlite
    GET    /database/show/mysql
    GET    /database/show/postgresql
    DELETE /database/delete/sqlite
    DELETE /database/delete/mysql
    DELETE /database/delete/postgresql
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

from ..services import auth, pydatabase as pyd
from ..services.pydatabase import Create, Show, Delete


router = APIRouter(prefix="/database", tags=["Database Management"])


# ──────────────────────────────────────────────
# REQUEST MODELS
# ──────────────────────────────────────────────

class CreateSQLiteRequest(BaseModel):
    db_name: str = Field(..., description="Nama file database SQLite (tanpa ekstensi .db)")


class CreateServerDBRequest(BaseModel):
    db_name: str = Field(..., description="Nama database yang akan dibuat")
    host: Optional[str] = Field(default="localhost", description="Host server")
    port: Optional[int] = Field(default=None, description="Port server (opsional)")


class DeleteSQLiteRequest(BaseModel):
    db_name: str = Field(..., description="Nama file database SQLite (sertakan ekstensi .db)")


class DeleteServerDBRequest(BaseModel):
    db_name: str = Field(..., description="Nama database yang akan dihapus")
    user: Optional[str] = Field(default="root")
    password: Optional[str] = Field(default="")
    host: Optional[str] = Field(default="localhost")
    port: Optional[int] = Field(default=None)

    @field_validator("db_name")
    def validate_db_name(cls, value: str) -> str:
        # Panggil fungsi validasi Anda di sini
        # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pyd.validate_db_name(value)


# ──────────────────────────────────────────────
# RESPONSE MODELS
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ShowSQLiteResponse(BaseModel):
    total: int
    databases: List[Dict[str, Any]]


class ShowServerDBResponse(BaseModel):
    total: int
    databases: List[str]


# ──────────────────────────────────────────────
# CREATE DATABASE
# ──────────────────────────────────────────────

@router.post(
    "/create/sqlite",
    response_model=MessageResponse,
    summary="Buat database SQLite",
    description="Membuat file database SQLite baru (.db) di direktori server.",
)
async def create_sqlite(body: CreateSQLiteRequest) -> MessageResponse:
    try:
        result = await Create(db_name=body.db_name).sqlite()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/create/mysql",
    response_model=MessageResponse,
    summary="Buat database MySQL",
    description="Membuat database baru di server MySQL / MariaDB.",
)
async def create_mysql(body: CreateServerDBRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        user = payload.get("sub")
        password = payload.get("pw")
        result = await Create(
            db_name=body.db_name,
            user=user,
            password=password,
            host=body.host,
            port=body.port,
        ).mysql()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/create/postgresql",
    response_model=MessageResponse,
    summary="Buat database PostgreSQL",
    description="Membuat database baru di server PostgreSQL.",
)
async def create_postgresql(body: CreateServerDBRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        result = await Create(
            db_name=body.db_name,
            user=payload.get("sub"),
            password=payload.get("pw"),
            host=body.host,
            port=body.port,
        ).postgresql()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ──────────────────────────────────────────────
# SHOW / LIST DATABASES
# ──────────────────────────────────────────────

@router.get(
    "/show/sqlite",
    response_model=ShowSQLiteResponse,
    summary="Lihat daftar database SQLite",
    description="Menampilkan semua file .db yang ditemukan di direktori yang ditentukan.",
)
async def show_sqlite(search_dir: str = ".") -> ShowSQLiteResponse:
    try:
        total, files = await Show().sqlite(search_dir=search_dir)
        databases: List[Dict[str, Any]] = [
            {"filename": f[0], "path": f[1], "size_bytes": f[2]}
            for f in files
        ]
        return ShowSQLiteResponse(total=total, databases=databases)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.get(
    "/show/mysql",
    response_model=ShowServerDBResponse,
    summary="Lihat daftar database MySQL",
    description="Menampilkan semua database yang ada di server MySQL.",
)
async def show_mysql(payload: Dict[str, Any] = Depends(auth.get_cookie), host: str = Query(default="localhost"), port: Optional[int] = Query(...)) -> ShowServerDBResponse:
    try:
        total, databases = await Show(user=payload.get("sub"), password=payload.get("pw"), host=host, port=port).mysql()
        return ShowServerDBResponse(total=total, databases=databases)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.get(
    "/show/postgresql",
    response_model=ShowServerDBResponse,
    summary="Lihat daftar database PostgreSQL",
    description="Menampilkan semua database yang ada di server PostgreSQL.",
)
async def show_postgresql(payload: Dict[str, Any] = Depends(auth.get_cookie), host: str = Query(default="localhost"), port: Optional[int] = Query(...)) -> ShowServerDBResponse:
    try:
        total, databases = await Show(user=payload.get("sub"), password=payload.get("pw"), host=host, port=port).postgresql()
        return ShowServerDBResponse(total=total, databases=databases)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ──────────────────────────────────────────────
# DELETE DATABASE
# ──────────────────────────────────────────────

@router.delete(
    "/delete/sqlite",
    response_model=MessageResponse,
    summary="Hapus database SQLite",
    description="Menghapus file database SQLite (.db) dari sistem.",
)
async def delete_sqlite(body: DeleteSQLiteRequest) -> MessageResponse:
    try:
        result = await Delete(db_name=body.db_name).sqlite()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete(
    "/delete/mysql",
    response_model=MessageResponse,
    summary="Hapus database MySQL",
    description="Menghapus database dari server MySQL. Database sistem tidak bisa dihapus.",
)
async def delete_mysql(body: DeleteServerDBRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        result = await Delete(
            db_name=body.db_name,
            user=payload.get("sub"),
            password=payload.get("pw"),
            host=body.host,
            port=body.port,
        ).mysql()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete(
    "/delete/postgresql",
    response_model=MessageResponse,
    summary="Hapus database PostgreSQL",
    description="Menghapus database dari server PostgreSQL. Database sistem tidak bisa dihapus.",
)
async def delete_postgresql(body: DeleteServerDBRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        result = await Delete(
            db_name=body.db_name,
            user=payload.get("sub"),
            password=payload.get("pw"),
            host=body.host,
            port=body.port,
        ).postgresql()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
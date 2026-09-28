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

from typing import Any

from fastapi import APIRouter, HTTPException, Depends

from ..schemas.database import (CreateSQLiteRequest, CreateServerDBRequest,
                                DeleteSQLiteRequest, DeleteServerDBRequest,
                                MessageResponse, ShowSQLiteResponse,
                                ShowServerDBResponse)
from ..services import auth
from ..services.pydatabase import Create, Show, Delete


router = APIRouter(prefix="/database", tags=["Backend - Database Management"])


class KukiProteksi(dict[str, Any]):
    """
    Kamus kustom untuk kuki yang akan langsung melempar error 
    jika data yang di-get() tidak ditemukan.
    """
    def get(self, key: str, default: Any = None) -> Any:
        # Jika kunci tidak ada di kuki, langsung potong aliran program dengan error
        if key not in self:
            raise KeyError(f"Data kuki kritis '{key}' tidak ditemukan!")
        
        # Jika ada, kembalikan nilainya secara normal
        return self[key]

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
async def create_mysql(body: CreateServerDBRequest, payload: dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        kuki=KukiProteksi(payload)
        result = await Create(
            db_name=body.db_name,
            user=kuki.get("sub"),
            password=kuki.get("pw"),
            host=kuki.get("host"),
            port=kuki.get("port")
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
async def create_postgresql(body: CreateServerDBRequest, payload: dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        kuki=KukiProteksi(payload)
        result = await Create(
            db_name=body.db_name,
            user=kuki.get("sub"),
            password=kuki.get("pw"),
            host=kuki.get("host"),
            port=kuki.get("port")
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
async def show_sqlite() -> ShowSQLiteResponse:
    try:
        total, files = await Show().sqlite()
        # databases: List[Any] = [
        #     # f.replace(".db", "")
        #     f
        #     for f in files
        # ]
        return ShowSQLiteResponse(total=total, databases=files)
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
async def show_mysql(payload: dict[str, Any] = Depends(auth.get_cookie)) -> ShowServerDBResponse:
    try:
        kuki=KukiProteksi(payload)
        total, databases = await Show(
            user=kuki.get("sub"),
            password=kuki.get("pw"),
            host=kuki.get("host"),
            port=kuki.get("port")
        ).mysql()
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
async def show_postgresql(payload: dict[str, Any] = Depends(auth.get_cookie)) -> ShowServerDBResponse:
    try:
        kuki=KukiProteksi(payload)
        total, databases = await Show(
            user=kuki.get("sub"),
            password=kuki.get("pw"),
            host=kuki.get("host"),
            port=kuki.get("port")
        ).postgresql()
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
async def delete_mysql(body: DeleteServerDBRequest, payload: dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        kuki=KukiProteksi(payload)
        result = await Delete(
            db_name=body.db_name,
            user=kuki.get("sub"),
            password=kuki.get("pw"),
            host=kuki.get("host"),
            port=kuki.get("port")
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
async def delete_postgresql(body: DeleteServerDBRequest, payload: dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        kuki=KukiProteksi(payload)
        result = await Delete(
            db_name=body.db_name,
            user=kuki.get("sub"),
            password=kuki.get("pw"),
            host=kuki.get("host"),
            port=kuki.get("port")
        ).postgresql()
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
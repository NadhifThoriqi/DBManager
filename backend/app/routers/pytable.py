"""
==============
api/api_table.py
==============
FastAPI APIRouter untuk operasi tabel database.
Hanya berisi definisi endpoint dan request/response model.
Seluruh logika bisnis ada di services/pytable.py.

Endpoint:
    POST   /table/list
    POST   /table/structure
    POST   /table/content
    POST   /table/create
    POST   /table/column/add
    POST   /table/insert
    PUT    /table/update
    DELETE /table/row
    DELETE /table/clear
    DELETE /table/drop
"""
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncEngine

from ..services import pytable as pt, auth
from ..schemas.table import (MessageResponse, ListTablesRequest,
                             ListTablesResponse, TableStructureResponse,
                             TableContentResponse, InspectStructureRequest,
                             ViewContentRequest, CreateTableRequest,
                             AddColumnRequest, InsertDataRequest,
                             UpdateDataRequest, DeleteRowRequest,
                             ClearTableRequest, DropTableRequest)
from ..schemas.auth import TypeDB

router = APIRouter(prefix="/table", tags=["Backend - Table Operations"])



# ──────────────────────────────────────────────
# HELPER: Buat engine dari config request
# ──────────────────────────────────────────────

async def _get_engine(
    body: ListTablesRequest,
    payload: Dict[str, Any] = Depends(auth.get_cookie)
):
    """Buat engine SQLAlchemy sesuai db_type secara dinamis."""

    # Ambil string db dari payload, amankan dengan .lower() jika ada
    db_raw = payload.get("db")
    if not db_raw:
        raise HTTPException(status_code=400, detail="Informasi database ('db') tidak ditemukan di cookie.")
        
    try:
        # Konversi ke TypeDB Enum dengan aman
        db_type = TypeDB(db_raw.lower())
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"db_type '{db_raw}' tidak dikenal. Pilih: sqlite | mysql | postgresql"
        )

    # Buat instance GetEngine
    ge = pt.GetEngine(
        db_name=body.db_name,
        host=payload.get("host"),
        port=payload.get("port"),
        user=payload.get("sub"),
        password=payload.get("pw")
    )
    
    # Cek tipe database langsung menggunakan Enum (Lebih bersih dan aman)
    if db_type == TypeDB.SQLITE:
        return await ge.sqlite()
    elif db_type == TypeDB.MYSQL:
        return await ge.mysql()
    elif db_type == TypeDB.POSTGRESQL:
        return await ge.postgresql()


# ──────────────────────────────────────────────
# HELPER: Konversi tipe string → SQLAlchemy type
# ──────────────────────────────────────────────

# Contoh yang robust:
def _resolve_column_type(type_str: str):
    from sqlalchemy import Integer, Float, Boolean, Text, String, Numeric, Date, DateTime
    t = type_str.strip().upper()
    if t in ("INTEGER", "INT"):
        return Integer()
    elif t in ("FLOAT", "REAL", "DOUBLE"):
        return Float()
    elif t in ("BOOLEAN", "BOOL"):
        return Boolean()
    elif t == "TEXT":
        return Text()
    elif t in ("NUMERIC", "DECIMAL"):
        return Numeric()
    elif t == "DATE":
        return Date()
    elif t in ("DATETIME", "TIMESTAMP"):
        return DateTime()
    elif t.startswith("VARCHAR"):
        try:
            length = int(t.replace("VARCHAR", "").strip("() "))
        except (ValueError, AttributeError):
            length = 255
        return String(length)
    else:
        return Text()


# ──────────────────────────────────────────────
# ENDPOINTS: INSPEKSI DATABASE
# ──────────────────────────────────────────────

@router.post(
    "/list",
    response_model=ListTablesResponse,
    summary="Daftar semua tabel",
    description="Mengambil semua nama tabel yang ada di database.",
)
async def list_table(
    engine: AsyncEngine = Depends(_get_engine)
) -> ListTablesResponse:
    try:
        tables = await pt.list_tables(engine)
        return ListTablesResponse(total=len(tables), tables=tables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


@router.post(
    "/structure",
    response_model=TableStructureResponse,
    summary="Lihat struktur kolom tabel",
    description="Menampilkan detail kolom: nama, tipe, primary key, nullable, default, dll.",
)
async def inspect_structure(
    body: InspectStructureRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> TableStructureResponse:
    try:
        raw_columns = await pt.inspect_table_structure(engine, body.table_name)
        columns:List[Dict[str, Any]] = [
            {**col, "type": str(col["type"])}
            for col in raw_columns
        ]
        return TableStructureResponse(table_name=body.table_name, columns=columns)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


@router.post(
    "/content",
    response_model=TableContentResponse,
    summary="Lihat isi data tabel",
    description="Mengambil baris data dari tabel dengan batas jumlah yang bisa dikonfigurasi.",
)
async def view_content(
    body: ViewContentRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> TableContentResponse:
    try:
        rows = await pt.view_table_content(engine, body.table_name, limit=body.limit)
        return TableContentResponse(table_name=body.table_name, limit=body.limit, rows=rows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


# ──────────────────────────────────────────────
# ENDPOINTS: DDL (Struktur Tabel)
# ──────────────────────────────────────────────

@router.post(
    "/create",
    response_model=MessageResponse,
    summary="Buat tabel baru",
    description=(
        "Membuat tabel baru secara dinamis. "
        "Kolom bernama 'id' otomatis dijadikan Primary Key."
    ),
)
async def create_table(
    body: CreateTableRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> MessageResponse:
    try:
        if not body.columns_def:
            raise ValueError("Minimal satu kolom harus didefinisikan")
       
        # Sekarang type_str[0] dijamin adalah Tipe SQL (str) dan type_str[1] adalah Indeks
        columns_def: Dict[str, Tuple[Any, Any]] = {
            col_name: (_resolve_column_type(col_data.type), col_data.index)
            for col_name, col_data in body.columns_def.items()
        }
        
        result = await pt.create_dynamic_table(engine, body.table_name, columns_def)
        return MessageResponse(message=result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/column/add",
    response_model=MessageResponse,
    summary="Tambah kolom baru ke tabel",
    description="Menambah kolom baru ke tabel yang sudah ada menggunakan ALTER TABLE.",
)
async def add_column(
    body: AddColumnRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> MessageResponse:
    try:
        result = await pt.add_new_column(engine, body.table_name, body.column_name, body.column_type)
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ──────────────────────────────────────────────
# ENDPOINTS: DML (Isi Data)
# ──────────────────────────────────────────────

@router.post(
    "/insert",
    response_model=MessageResponse,
    summary="Insert satu baris data",
    description="Menambahkan satu baris data ke dalam tabel (parameterized query, aman dari SQL Injection).",
)
async def insert_data(
    body: InsertDataRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> MessageResponse:
    try:
        result = await pt.insert_dynamic_data(engine, body.table_name, body.data)
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.put(
    "/update",
    response_model=MessageResponse,
    summary="Update data di tabel",
    description=(
        "Memperbarui baris data dengan kondisi WHERE. "
        "Gunakan placeholder :nama di condition_str. "
        "Contoh: condition_str='id = :target_id', condition_params={\"target_id\": 1}."
    ),
)
async def update_data(
    body: UpdateDataRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> MessageResponse:
    try:
        result = await pt.update_table_data(
            engine,
            body.table_name,
            body.update_values,
            body.condition_str,
            body.condition_params,
        )
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ──────────────────────────────────────────────
# ENDPOINTS: HAPUS DATA / TABEL
# ──────────────────────────────────────────────

@router.delete(
    "/row",
    response_model=MessageResponse,
    summary="Hapus satu baris data",
    description=(
        "Menghapus baris data berdasarkan kondisi WHERE. "
        "Contoh: condition_str='id = :target_id', condition_params={\"target_id\": 5}."
    ),
)
async def delete_row(
    body: DeleteRowRequest,
    engine: AsyncEngine = Depends(_get_engine)
) -> MessageResponse:
    try:
        result = await pt.delete_one_row(
            engine, body.table_name, body.condition_str, body.condition_params
        )
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete(
    "/clear",
    response_model=MessageResponse,
    summary="Kosongkan semua data di tabel",
    description=(
        "Menghapus seluruh isi data di tabel TANPA menghapus struktur tabelnya. "
        "SQLite: DELETE FROM. MySQL/PostgreSQL: TRUNCATE TABLE."
    ),
)
async def clear_table(
    body: ClearTableRequest,
    engine: AsyncEngine = Depends(_get_engine),
    payload: Dict[str, Any] = Depends(auth.get_cookie)
) -> MessageResponse:
    try:
        result = await pt.clear_table_data(engine, body.table_name, db_type=TypeDB(payload.get("db")))
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete(
    "/drop",
    response_model=MessageResponse,
    summary="Hapus tabel secara permanen",
    description="⚠️ Menghapus tabel beserta seluruh datanya secara permanen. Tidak dapat dibatalkan!",
)
async def drop_table(
    body: DropTableRequest,
    engine: AsyncEngine = Depends(_get_engine),
    payload: Dict[str, Any] = Depends(auth.get_cookie)
) -> MessageResponse:
    try:
        result = await pt.drop_table(
            engine,
            body.table_name,
            TypeDB(payload.get("db"))
        )
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

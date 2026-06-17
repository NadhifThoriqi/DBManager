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

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services import pytable as pt, auth

router = APIRouter(prefix="/table", tags=["Table Operations"])


# ──────────────────────────────────────────────
# HELPER: Buat engine dari config request
# ──────────────────────────────────────────────

def _get_engine(
    db_type: str,
    db_name: str,
    host: Optional[str],
    port: Optional[int],
    user: Optional[str],
    password: Optional[str],
):
    """Buat engine SQLAlchemy sesuai db_type."""
    ge = pt.GetEngine(
        db_name=db_name,
        host=host or "localhost",
        port=port,
        user=user or "root",
        password=password or "",
    )
    db_type_lower = db_type.lower()
    if db_type_lower == "sqlite":
        return ge.sqlite()
    elif db_type_lower == "mysql":
        return ge.mysql()
    elif db_type_lower == "postgresql":
        return ge.postgresql()
    else:
        raise ValueError(
            f"db_type tidak dikenal: '{db_type}'. Pilih: sqlite | mysql | postgresql"
        )


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
# SHARED BASE REQUEST MODEL
# ──────────────────────────────────────────────

class EngineConfig(BaseModel):
    """Konfigurasi koneksi database yang digunakan di semua request."""
    db_type: Literal["sqlite", "mysql", "postgresql"] = Field(
        ...,
        description="Jenis database: sqlite | mysql | postgresql",
    )
    db_name: str = Field(
        ...,
        description=(
            "Nama database atau path file SQLite. "
            "Contoh SQLite: 'toko.db' | MySQL/PgSQL: 'toko_db'"
        ),
    )
    host: Optional[str] = Field(default="localhost", description="Host server (MySQL/PgSQL)")
    port: Optional[int] = Field(default=None, description="Port server (MySQL/PgSQL)")


# ──────────────────────────────────────────────
# RESPONSE MODELS
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ListTablesResponse(BaseModel):
    total: int
    tables: List[str]


class TableStructureResponse(BaseModel):
    table_name: str
    columns: List[Dict[str, Any]]


class TableContentResponse(BaseModel):
    table_name: str
    limit: int
    rows: List[Dict[str, Any]]


# ──────────────────────────────────────────────
# REQUEST BODY MODELS
# ──────────────────────────────────────────────

class ListTablesRequest(EngineConfig):
    pass


class InspectStructureRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang ingin di-inspect")


class ViewContentRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel")
    limit: int = Field(
        default=10, ge=1, le=1000,
        description="Jumlah baris maksimum yang diambil (1–1000, default: 10)",
    )


class CreateTableRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel baru yang akan dibuat")
    columns_def: Dict[str, str] = Field(
        ...,
        description=(
            "Definisi kolom: {nama_kolom: tipe_sql}. "
            "Kolom bernama 'id' otomatis dijadikan Primary Key."
        ),
        examples=[{
            "id": "INTEGER",
            "nama": "VARCHAR(100)",
            "harga": "FLOAT",
            "stok": "INTEGER",
            "is_aktif": "BOOLEAN",
        },]
    )


class AddColumnRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang akan ditambah kolomnya")
    column_name: str = Field(..., description="Nama kolom baru")
    column_type: str = Field(
        ...,
        description="Tipe SQL kolom mentah, contoh: 'TEXT', 'VARCHAR(50)', 'INTEGER'",
    )


class InsertDataRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel tujuan")
    data: Dict[str, Any] = Field(
        ...,
        description="Data yang akan diinsert: {nama_kolom: nilai}",
        examples=[{"nama": "Laptop ASUS", "harga": 12500000.0, "stok": 15, "is_aktif": True},]
    )


class UpdateDataRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel")
    update_values: Dict[str, Any] = Field(
        ...,
        description="Data yang akan diperbarui: {nama_kolom: nilai_baru}",
        examples=[{"stok": 50, "harga": 11000000.0},]
    )
    condition_str: str = Field(
        ...,
        description="Kondisi WHERE dengan placeholder SQLAlchemy, contoh: 'id = :target_id'",
    )
    condition_params: Dict[str, Any] = Field(
        ...,
        description="Nilai untuk placeholder, contoh: {\"target_id\": 1}",
    )


class DeleteRowRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel")
    condition_str: str = Field(
        ...,
        description="Kondisi WHERE dengan placeholder, contoh: 'id = :target_id'",
    )
    condition_params: Dict[str, Any] = Field(
        ...,
        description="Nilai untuk placeholder, contoh: {\"target_id\": 3}",
    )


class ClearTableRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang akan dikosongkan datanya")


class DropTableRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang akan dihapus secara permanen")


# ──────────────────────────────────────────────
# ENDPOINTS: INSPEKSI DATABASE
# ──────────────────────────────────────────────

@router.post(
    "/list",
    response_model=ListTablesResponse,
    summary="Daftar semua tabel",
    description="Mengambil semua nama tabel yang ada di database.",
)
def list_tables(body: ListTablesRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> ListTablesResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        tables = pt.list_tables(engine)
        return ListTablesResponse(total=len(tables), tables=tables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/structure",
    response_model=TableStructureResponse,
    summary="Lihat struktur kolom tabel",
    description="Menampilkan detail kolom: nama, tipe, primary key, nullable, default, dll.",
)
def inspect_structure(body: InspectStructureRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> TableStructureResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        raw_columns = pt.inspect_table_structure(engine, body.table_name)
        columns:List[Dict[str, Any]] = [
            {**col, "type": str(col["type"])}
            for col in raw_columns
        ]
        return TableStructureResponse(table_name=body.table_name, columns=columns)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/content",
    response_model=TableContentResponse,
    summary="Lihat isi data tabel",
    description="Mengambil baris data dari tabel dengan batas jumlah yang bisa dikonfigurasi.",
)
def view_content(body: ViewContentRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> TableContentResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        rows = pt.view_table_content(engine, body.table_name, limit=body.limit)
        return TableContentResponse(table_name=body.table_name, limit=body.limit, rows=rows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


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
def create_table(body: CreateTableRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        if not body.columns_def:
            raise ValueError("Minimal satu kolom harus didefinisikan")
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        columns_def = {
            col_name: _resolve_column_type(type_str)
            for col_name, type_str in body.columns_def.items()
        }
        
        result = pt.create_dynamic_table(engine, body.table_name, columns_def)
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
def add_column(body: AddColumnRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = pt.add_new_column(engine, body.table_name, body.column_name, body.column_type)
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
def insert_data(body: InsertDataRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = pt.insert_dynamic_data(engine, body.table_name, body.data)
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
def update_data(body: UpdateDataRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = pt.update_table_data(
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
def delete_row(body: DeleteRowRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = pt.delete_one_row(
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
def clear_table(body: ClearTableRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = pt.clear_table_data(engine, body.table_name, db_type=body.db_type)
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
def drop_table(body: DropTableRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = pt.drop_table(engine, body.table_name)
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
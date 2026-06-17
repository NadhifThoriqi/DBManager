# NovDB — API Reference

Dokumen ini menjelaskan semua endpoint REST API yang dibutuhkan oleh frontend **NovDB**.
Implementasi backend menggunakan **Python FastAPI**.

---

## Base URL

```
http://localhost:8000/api
```

Ubah hanya konstanta `API_CONFIG.BASE_URL` di `api.js`, atau melalui halaman **Settings** di UI.

---

## Endpoints

### 1. Health Check

```
GET /api/health
```

**Response** `200 OK`
```json
{ "status": "ok", "version": "1.0.0" }
```

---

### 2. Daftar Tabel

```
GET /api/tables
```

**Response** `200 OK` — salah satu format berikut:

```json
["users", "products", "orders"]
```

```json
[
  { "name": "users",    "row_count": 120 },
  { "name": "products", "row_count": 45  }
]
```

```json
{ "tables": ["users", "products"] }
```

---

### 3. Data Tabel (dengan pagination & filter)

```
GET /api/table/{table_name}?page=1&limit=25&search=admin&sort=id&order=asc
```

| Query Param | Tipe    | Default | Keterangan                     |
|-------------|---------|---------|--------------------------------|
| `page`      | integer | 1       | Nomor halaman                  |
| `limit`     | integer | 25      | Baris per halaman              |
| `search`    | string  | –       | Cari di semua kolom teks       |
| `sort`      | string  | –       | Nama kolom untuk sorting       |
| `order`     | string  | `asc`   | `asc` atau `desc`              |

**Response** `200 OK`
```json
{
  "data": [
    { "id": 1, "name": "Alice", "email": "alice@example.com" }
  ],
  "total": 120,
  "page": 1,
  "pages": 5
}
```

---

### 4. Tambah Data

```
POST /api/table/{table_name}
```

**Body** `application/json`
```json
{ "name": "Alice", "email": "alice@example.com" }
```

**Response** `201 Created`
```json
{ "id": 42, "name": "Alice", "email": "alice@example.com" }
```

---

### 5. Update Data

```
PUT /api/table/{table_name}/{id}
```

**Body** `application/json`
```json
{ "name": "Alice Updated" }
```

**Response** `200 OK`
```json
{ "id": 42, "name": "Alice Updated", "email": "alice@example.com" }
```

---

### 6. Hapus Data

```
DELETE /api/table/{table_name}/{id}
```

**Response** `200 OK`
```json
{ "message": "Data berhasil dihapus.", "id": 42 }
```

---

### 7. Eksekusi SQL Query

```
POST /api/query
```

**Body**
```json
{ "query": "SELECT * FROM users WHERE id < 10" }
```

**Response sukses** `200 OK`
```json
{
  "rows": [
    { "id": 1, "name": "Alice" }
  ],
  "affected_rows": null,
  "execution_time": 0.012
}
```

**Response DML** (INSERT/UPDATE/DELETE)
```json
{
  "rows": [],
  "affected_rows": 3,
  "execution_time": 0.008
}
```

---

### 8. Statistik (Opsional)

```
GET /api/stats
```

**Response** `200 OK`
```json
{
  "databases": 1,
  "tables": 5,
  "total_records": 1234
}
```

> Jika endpoint ini tidak tersedia, frontend akan menghitung sendiri dari `/api/tables`.

---

## Error Format

Semua error harus menggunakan format FastAPI default:

```json
{ "detail": "Pesan error yang deskriptif" }
```

atau

```json
{ "message": "Pesan error" }
```

Status code yang digunakan:

| Code | Arti                                  |
|------|---------------------------------------|
| 400  | Bad Request (query/data tidak valid)  |
| 404  | Table atau record tidak ditemukan     |
| 422  | Validation error (FastAPI default)    |
| 500  | Internal Server Error                 |

---

## Contoh Implementasi Python FastAPI (Minimal)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Wajib: izinkan CORS dari frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Ganti dengan origin spesifik di production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/tables")
def get_tables():
    # Query ke database Anda
    return [{"name": "users", "row_count": 10}]

@app.get("/api/table/{table_name}")
def get_table(table_name: str, page: int = 1, limit: int = 25,
              search: str = "", sort: str = "", order: str = "asc"):
    # Implementasi query dengan pagination
    ...

@app.post("/api/table/{table_name}")
def create_record(table_name: str, payload: dict):
    ...

@app.put("/api/table/{table_name}/{id}")
def update_record(table_name: str, id: int, payload: dict):
    ...

@app.delete("/api/table/{table_name}/{id}")
def delete_record(table_name: str, id: int):
    ...

@app.post("/api/query")
def execute_query(body: dict):
    query = body.get("query", "")
    # Jalankan query, kembalikan rows
    ...
```

---

## Catatan Penting

- **CORS**: Pastikan backend mengizinkan request dari origin frontend Anda.
- **ID Field**: Frontend mengasumsikan primary key bernama `id` atau `ID`. Jika berbeda, kolom pertama akan digunakan.
- **Pagination**: Jika backend mengembalikan array biasa (tanpa `total`/`pages`), frontend akan menganggap semua data sudah di-load dalam satu halaman.

# DBManager

Konsol admin berbasis web untuk mengelola database **SQLite**, **MySQL**, dan **PostgreSQL** dari satu antarmuka, mirip phpMyAdmin versi ringan. Backend dibangun dengan **FastAPI + SQLAlchemy (async)**, frontend berupa **vanilla JavaScript (ES Modules)** tanpa framework dan tanpa proses build.

## Fitur

- **Autentikasi berbasis cookie**: login dengan kredensial server database (user, password, host, port, tipe DB). Sesi disimpan sebagai JWT di cookie `HttpOnly`.
- **Manajemen database**: buat, lihat daftar, dan hapus database untuk SQLite, MySQL, dan PostgreSQL. Database sistem (`mysql`, `information_schema`, `postgres`, `template0/1`, dll.) dilindungi dari penghapusan.
- **Operasi tabel**:
  - lihat daftar tabel, struktur kolom (termasuk primary key dan foreign key), dan isi data
  - buat tabel baru dengan definisi kolom dan indeks (`primary`, `unique`, `index`, `fulltext`, `spatial`)
  - tambah kolom (`ALTER TABLE`)
  - insert, update, dan hapus baris
  - kosongkan tabel (`DELETE` / `TRUNCATE`) dan hapus tabel (`DROP`)
- **Designer**: diagram relasi antar tabel (kartu tabel dan garis foreign key) yang bisa di-drag, di-pan, dan di-zoom, termasuk pinch-to-zoom di layar sentuh. Posisi kartu diingat per database.
- **Konversi tipe otomatis**: nilai dari JSON (misalnya string tanggal ISO atau UUID) dikonversi sesuai tipe kolom sebelum dikirim ke database, sehingga driver yang ketat seperti `asyncpg` tidak menolaknya.
- **Dokumentasi API interaktif** bawaan FastAPI di `/docs` dan `/redoc`.

## Struktur Proyek

```
DBManager/
├── main.py                  # Entry point FastAPI (CORS, static files, router)
├── requirements.txt
├── .env.example             # Contoh konfigurasi environment
├── sql/                     # File database SQLite (dibuat otomatis)
├── backend/
│   ├── __init__.py          # Menggabungkan semua router backend
│   └── app/
│       ├── core/            # Enum bersama (jenis indeks)
│       ├── routers/         # Endpoint: auth, pydatabase, pytable
│       ├── schemas/         # Model request/response (Pydantic)
│       └── services/        # Logika bisnis: auth, pydatabase, pytable
└── frontend/
    ├── __init__.py          # Router yang menyajikan index.html
    ├── index.html
    └── assets/
        ├── css/             # base, layout, components, auth, designer
        └── js/
            ├── app.js       # Entry point, App Shell, dan routing antar view
            ├── config.js    # Base URL API (disimpan di localStorage)
            ├── state.js     # State global sederhana
            ├── api/         # Pembungkus fetch: client, auth, database, table
            ├── ui/          # Modal, toast, ikon, helper
            └── views/       # auth, dashboard, databases, tables, designer
```

Pemisahan tanggung jawab di backend: **router** hanya berisi definisi endpoint, **schemas** berisi validasi input, dan seluruh logika ada di **services**.

## Prasyarat

- Python 3.11 atau lebih baru (`StrEnum` dipakai di kode)
- Salah satu server database (opsional untuk SQLite): MySQL/MariaDB atau PostgreSQL

## Instalasi

```bash
# 1. Buat dan aktifkan virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependensi
pip install -r requirements.txt

# 3. Install driver database sesuai kebutuhan (pilih yang dipakai saja)
pip install aiosqlite            # SQLite
pip install asyncmy              # MySQL / MariaDB
pip install asyncpg              # PostgreSQL
```

> **Catatan:** kode memakai `from dotenv import load_dotenv`, yang berasal dari paket **`python-dotenv`**. Jika muncul `ImportError` atau `load_dotenv` tidak ditemukan, jalankan `pip install python-dotenv` dan ganti baris `dotenv` di `requirements.txt` menjadi `python-dotenv`.

## Konfigurasi

Salin `.env.example` menjadi `.env`, lalu isi `SECRET_KEY` dengan string acak yang panjang:

```bash
cp .env.example .env
```

```env
SECRET_KEY="isi_dengan_string_acak_yang_panjang"
```

Membuat kunci acak:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Aplikasi akan berhenti dengan `RuntimeError` saat startup jika `SECRET_KEY` tidak ditemukan.

## Menjalankan

```bash
python main.py
```

Server berjalan di `http://127.0.0.1:2606` dengan auto-reload. Cara lain:

```bash
uvicorn main:app --host 0.0.0.0 --port 2606 --reload
```

| Alamat | Fungsi |
|---|---|
| `http://127.0.0.1:2606/` | Antarmuka web |
| `http://127.0.0.1:2606/docs` | Swagger UI |
| `http://127.0.0.1:2606/health` | Health check |

Aplikasi dikonfigurasi dengan `root_path="/thorix"` agar sinkron dengan reverse proxy Nginx pada path `/thorix/`. Aset frontend pada `index.html` juga dimuat lewat prefix tersebut. Jika Anda menjalankannya tanpa Nginx atau memakai path lain, sesuaikan `root_path` di `main.py` dan tautan aset di `frontend/index.html`.

## Cara Pakai

1. Buka antarmuka web dan login dengan memilih **tipe database**, mengisi **host**, **port**, **username**, dan **password**.
   - SQLite tidak memakai kredensial server (isi port `0`).
   - Port bawaan: MySQL `3306`, PostgreSQL `5432`.
2. Buka **Databases** untuk membuat atau menghapus database.
3. Buka **Tables**, pilih database lalu tabel, kemudian gunakan tab *Data*, *Struktur*, *Insert Row*, *Tambah Kolom*, atau *Danger Zone*.
4. Buka **Designer** untuk melihat relasi antar tabel.

Jika API berjalan di alamat lain, ubah lewat tombol **Server** di topbar. Nilainya disimpan di `localStorage` browser.

## Ringkasan API

Semua endpoint selain `/auth/signin` membutuhkan cookie `access_token`.

**Auth**

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/auth/signin` | Login dan set cookie sesi |
| POST | `/auth/logout` | Hapus cookie sesi |

**Database**

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/database/create/{sqlite\|mysql\|postgresql}` | Buat database |
| GET | `/database/show/{sqlite\|mysql\|postgresql}` | Daftar database |
| DELETE | `/database/delete/{sqlite\|mysql\|postgresql}` | Hapus database |

**Tabel** (body selalu memuat `db_name`)

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/table/list` | Daftar tabel |
| POST | `/table/structure` | Struktur kolom |
| POST | `/table/content` | Isi tabel (`limit` 1–1000) |
| POST | `/table/create` | Buat tabel |
| POST | `/table/column/add` | Tambah kolom |
| POST | `/table/insert` | Insert satu baris |
| PUT | `/table/update` | Update baris dengan kondisi `WHERE` |
| DELETE | `/table/row` | Hapus baris dengan kondisi `WHERE` |
| DELETE | `/table/clear` | Kosongkan tabel |
| DELETE | `/table/drop` | Hapus tabel permanen |

Contoh update dengan placeholder berparameter:

```json
{
  "db_name": "toko_db",
  "table_name": "produk",
  "update_values": { "stok": 50, "harga": 11000000.0 },
  "condition_str": "id = :target_id",
  "condition_params": { "target_id": 1 }
}
```

## Catatan Keamanan

Proyek ini adalah alat admin. Baca poin berikut sebelum memakainya di luar mesin lokal:

- **Password database ikut tersimpan di JWT** (klaim `pw`). JWT hanya ditandatangani, tidak dienkripsi, sehingga isinya bisa dibaca siapa pun yang memegang cookie. Pertimbangkan menyimpan kredensial di sisi server (session store) atau mengenkripsinya.
- **Cookie** diatur `secure=False`. Ubah ke `True` di `services/auth.py` saat dilayani lewat HTTPS.
- **CORS** saat ini `allow_origins=["*"]` dengan `allow_credentials=True`. Batasi ke origin yang dipercaya untuk produksi.
- **`condition_str`** pada update dan delete berupa fragmen SQL mentah dari klien. Nilainya diparameterisasi, tetapi string kondisinya sendiri tidak. Jangan buka aplikasi ini ke pengguna yang tidak dipercaya.
- **`add_new_column`** menyusun `ALTER TABLE` dari nama kolom dan tipe yang dikirim klien tanpa validasi identifier di layanan.
- Endpoint **clear**, **drop**, dan **delete database** bersifat permanen dan tidak bisa dibatalkan.

## Teknologi

- **Backend:** FastAPI, Uvicorn, SQLAlchemy async, SQLModel, Pydantic, PyJWT, Jinja2
- **Driver:** aiosqlite, asyncmy, asyncpg
- **Frontend:** JavaScript ES Modules, CSS murni

## Lisensi

Belum ditentukan. Tambahkan berkas `LICENSE` sesuai kebutuhan.

# DBManager

DBManager adalah aplikasi web berbasis **FastAPI** untuk mengelola database (SQLite, MySQL, dan PostgreSQL) beserta tabel dan isi datanya melalui satu antarmuka (UI) maupun REST API. Aplikasi ini terdiri dari dua bagian utama:

- **Backend** — REST API (FastAPI) untuk autentikasi, manajemen database, dan manajemen tabel.
- **Frontend** — antarmuka web statis (HTML/CSS/JavaScript) yang dikirim langsung oleh FastAPI, dipakai untuk berinteraksi dengan API secara visual (mirip phpMyAdmin sederhana).

---

## 1. Cara Kerja Program

### 1.1 Alur Umum

1. `main.py` adalah **entry point** aplikasi. Saat dijalankan, ia membuat instance `FastAPI`, mengaktifkan CORS, mem-mount folder statis frontend (`/assets`), lalu mendaftarkan dua kelompok router:
   - `backend.run` → seluruh endpoint API (`/auth`, `/database`, `/table`)
   - `frontend.run` → endpoint yang merender halaman `index.html`
2. Pengguna membuka halaman utama (`/`) yang berisi UI DBManager (dibangun dengan JavaScript modular di `frontend/assets/js`).
3. Pengguna **login** melalui `POST /auth/signin` dengan mengisi kredensial database (username, password, host, port, dan jenis database: `sqlite` / `mysql` / `postgresql`).
4. Kredensial tersebut dikemas menjadi **JWT (JSON Web Token)** dan disimpan sebagai **cookie HTTPOnly** (`access_token`) di browser — bukan disimpan di server. Ini berarti server bersifat *stateless*: setiap request membawa kredensialnya sendiri di dalam cookie yang telah dienkripsi.
5. Setiap kali endpoint yang membutuhkan koneksi ke MySQL/PostgreSQL dipanggil, FastAPI akan menjalankan dependency `get_cookie` yang membaca dan memvalidasi JWT dari cookie tersebut, lalu mengambil kembali kredensial (`user`, `password`, `host`, `port`, `db`) untuk membuat koneksi database secara dinamis.
6. Semua operasi database dijalankan secara **asynchronous** menggunakan SQLAlchemy Async Engine (`aiosqlite`, `asyncmy`, `asyncpg`), sehingga performa tetap baik meski menangani banyak request bersamaan.

### 1.2 Struktur Direktori

```
DBManager/
├── main.py                     # Entry point aplikasi FastAPI
├── requirements.txt             # Daftar dependensi Python
├── .env.example                 # Contoh file environment variable
│
├── backend/                     # Seluruh logika backend (API)
│   ├── __init__.py               # Menggabungkan semua router backend
│   └── app/
│       ├── core/
│       │   └── enums.py          # Enum jenis indeks kolom (PRIMARY, UNIQUE, dst)
│       ├── routers/               # Definisi endpoint (HTTP layer)
│       │   ├── auth.py              # /auth/signin, /auth/logout
│       │   ├── pydatabase.py        # /database/create, /show, /delete
│       │   └── pytable.py           # /table/list, /structure, /content, dst
│       ├── schemas/                # Model Pydantic (validasi request/response)
│       │   ├── auth.py
│       │   ├── database.py
│       │   └── table.py
│       └── services/                # Logika bisnis (Service layer)
│           ├── auth.py               # Pembuatan & validasi JWT/cookie
│           ├── pydatabase.py         # Create/Show/Delete database
│           └── pytable.py            # CRUD tabel & data
│
└── frontend/                    # Antarmuka web (UI)
    ├── __init__.py                # Router untuk merender index.html
    ├── index.html                 # Halaman utama
    └── assets/
        ├── css/                    # Styling UI
        └── js/                     # Logika UI (API client, state, views)
```

### 1.3 Konsep Arsitektur

Backend mengikuti pola **Router → Schema → Service**:

| Layer | Tugas |
|---|---|
| **Router** (`routers/`) | Menentukan endpoint HTTP (path, method), menangani request/response, dan meneruskan pekerjaan ke *service*. |
| **Schema** (`schemas/`) | Mendefinisikan bentuk data (Pydantic model) untuk validasi otomatis input & output. |
| **Service** (`services/`) | Berisi seluruh logika bisnis nyata: membuat koneksi database, menjalankan query SQL, memproses data. |

Pemisahan ini membuat kode lebih mudah dirawat: jika logika database berubah, cukup ubah file di `services/` tanpa menyentuh endpoint API.

### 1.4 Fitur Utama API

**Autentikasi (`/auth`)**
- `POST /auth/signin` — Login dan membuat cookie JWT berisi kredensial database.
- `POST /auth/logout` — Menghapus cookie sesi.

**Manajemen Database (`/database`)**
- `POST /database/create/{sqlite|mysql|postgresql}` — Membuat database baru.
- `GET /database/show/{sqlite|mysql|postgresql}` — Menampilkan daftar database.
- `DELETE /database/delete/{sqlite|mysql|postgresql}` — Menghapus database (database sistem dilindungi otomatis).

**Manajemen Tabel (`/table`)**
- `POST /table/list` — Daftar tabel dalam database.
- `POST /table/structure` — Struktur kolom tabel.
- `POST /table/content` — Isi data tabel.
- `POST /table/create` — Membuat tabel baru secara dinamis.
- `POST /table/column/add` — Menambah kolom baru.
- `POST /table/insert` — Menambah satu baris data.
- `PUT /table/update` — Memperbarui data berdasarkan kondisi.
- `DELETE /table/row` — Menghapus satu baris data.
- `DELETE /table/clear` — Mengosongkan seluruh isi tabel.
- `DELETE /table/drop` — Menghapus tabel secara permanen.

Semua endpoint di atas terdokumentasi otomatis oleh FastAPI dan dapat dicoba langsung lewat **Swagger UI** di `/docs` (lihat bagian [Menjalankan Program](#3-cara-menjalankan-program)).

---

## 2. Cara Pemasangan (Instalasi Library & Framework)

### 2.1 Prasyarat

- **Python 3.11+** (karena memakai `enum.StrEnum`, fitur baru di Python 3.11)
- `pip` sudah terpasang
- (Opsional) Server **MySQL/MariaDB** dan/atau **PostgreSQL** jika ingin memakai selain SQLite

### 2.2 Buat Virtual Environment (disarankan)

```bash
python3 -m venv venv

# Aktivasi di Linux/Mac
source venv/bin/activate

# Aktivasi di Windows
venv\Scripts\activate
```

### 2.3 Install Dependensi Utama

Install seluruh library wajib yang tercantum di `requirements.txt`:

```bash
pip install -r requirements.txt
```

Isi `requirements.txt`:

```
fastapi
uvicorn
pydantic
dotenv
PyJwt
types-PyJWT
jinja2
sqlmodel
```

### 2.4 Install Driver Database (sesuai kebutuhan)

Driver database **tidak** diinstal otomatis oleh `requirements.txt` (dikomentari) karena tidak semua orang memakai ketiga jenis database. Pilih sesuai yang akan dipakai:

```bash
# Untuk SQLite (disarankan selalu diinstal, driver ringan)
pip install aiosqlite

# Untuk MySQL / MariaDB
pip install asyncmy

# Untuk PostgreSQL
pip install asyncpg
```

> 💡 Jika hanya ingin mencoba aplikasi dengan cepat, cukup install `aiosqlite` karena SQLite tidak membutuhkan server database eksternal.

### 2.5 Konfigurasi Environment Variable

Buat file `.env` di root folder (sejajar dengan `main.py`), isinya menyalin dari `.env.example`:

```bash
cp .env.example .env
```

Lalu isi `SECRET_KEY` dengan string acak yang aman (dipakai untuk menandatangani JWT):

```env
SECRET_KEY = "ganti-dengan-string-rahasia-yang-panjang-dan-acak"
```

⚠️ **Penting:** Jangan pernah membiarkan `SECRET_KEY` default atau mengunggahnya ke repository publik, karena kunci ini melindungi cookie autentikasi pengguna.

---

## 3. Cara Menjalankan Program

### 3.1 Jalankan Server

Ada dua cara menjalankan aplikasi:

**Cara 1 — Langsung lewat Python:**

```bash
python main.py
```

**Cara 2 — Lewat Uvicorn (disarankan untuk development, mendukung auto-reload):**

```bash
uvicorn main:app --host 0.0.0.0 --port 2606 --reload
```

Setelah berjalan, server dapat diakses di:

- **UI DBManager**: http://localhost:2606/thorix/
- **Dokumentasi API (Swagger UI)**: http://localhost:2606/thorix/docs
- **Dokumentasi API (ReDoc)**: http://localhost:2606/thorix/redoc
- **Health check**: http://localhost:2606/thorix/health

> ℹ️ Aplikasi ini menggunakan `root_path="/thorix"` (lihat `main.py`), yang berarti seluruh route otomatis berada di bawah prefix `/thorix`. Ini biasanya digunakan saat aplikasi dijalankan di belakang reverse proxy seperti Nginx. Jika ingin menghapus prefix ini untuk pengujian lokal biasa, ubah/hapus parameter `root_path` pada `FastAPI(...)` di `main.py`.

### 3.2 Login Pertama Kali

1. Buka UI di browser (`http://localhost:2606/thorix/`).
2. Isi form login dengan:
   - **Jenis database**: `sqlite`, `mysql`, atau `postgresql`
   - **Username, Password, Host, Port** (untuk SQLite, kredensial ini tidak wajib dipakai secara aktif, tapi tetap harus diisi karena bagian dari skema request)
3. Setelah login berhasil, cookie `access_token` otomatis tersimpan di browser dan Anda dapat langsung mengelola database & tabel dari UI.

### 3.3 Contoh Penggunaan API Secara Langsung (opsional)

Membuat database SQLite baru via `curl`:

```bash
curl -X POST "http://localhost:2606/thorix/database/create/sqlite" \
  -H "Content-Type: application/json" \
  -d '{"db_name": "toko"}'
```

Login untuk mendapatkan cookie sesi:

```bash
curl -X POST "http://localhost:2606/thorix/auth/signin" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"user":"root","password":"secret","host":"localhost","port":3306,"db":"mysql"}'
```

Selanjutnya gunakan `cookies.txt` (`-b cookies.txt`) pada request lain yang membutuhkan sesi login (misalnya operasi tabel MySQL/PostgreSQL).

### 3.4 Menghentikan Server

Tekan `CTRL + C` di terminal tempat server berjalan.

---

## 4. Catatan Keamanan

- Password database dikirim & disimpan di dalam JWT (cookie HTTPOnly), **bukan** di database aplikasi — pastikan `SECRET_KEY` benar-benar rahasia.
- Set `secure=True` pada cookie (`backend/app/services/auth.py`) jika aplikasi sudah berjalan di atas HTTPS pada production.
- Semua nama tabel/database divalidasi (`validate_db_name`) agar hanya berisi huruf, angka, dan underscore, untuk mencegah SQL Injection lewat nama identifier.
- Query data (insert/update/delete) menggunakan *parameterized query* SQLAlchemy sehingga aman dari SQL Injection pada bagian nilai (value).
- Database sistem bawaan MySQL/PostgreSQL (misalnya `mysql`, `information_schema`, `postgres`, `template0/1`) dilindungi dari penghapusan.

---

## 5. Lisensi

Silakan sesuaikan bagian ini dengan lisensi yang ingin digunakan untuk proyek Anda (misalnya MIT, Apache 2.0, atau proprietary/internal use only).

import uvicorn
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import backend
import frontend


@asynccontextmanager
async def lifespan(life_app: FastAPI):
    """
    Konteks manajer lifecycle aplikasi FastAPI.

    Dijalankan saat startup:
        - Mencetak nama aplikasi yang sedang berjalan.
        - Menginisialisasi database (membuat tabel jika belum ada).

    Dijalankan saat shutdown:
        - Mencetak pesan bahwa aplikasi sedang dimatikan.

    Args:
        life_app (FastAPI): Instance aplikasi FastAPI yang sedang berjalan.
    """
    # --- DIJALANKAN SAAT STARTUP ---
    # Menggunakan 'life_app' agar tidak kena error W0613 (Unused argument)
    print(f"Aplikasi {life_app.title} sedang berjalan...")

    yield

    # --- DIJALANKAN SAAT SHUTDOWN ---
    print("Aplikasi sedang dimatikan...")

    
# PENTING: Tambahkan root_path agar sinkron dengan Nginx /thorix/
app = FastAPI(
    title="DBManager",
    # docs_url=None,
    # redoc_url=None,
    root_path="/thorix",
    lifespan=lifespan
)

ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["DELETE", "GET", "POST", "PUT", "PATCH"],
    allow_headers=["*"],
)

direktori_skrip = Path(__file__).resolve().parent
# Mount folder static untuk JavaScript/CSS Frontend
app.mount(
    "/assets",
    StaticFiles(
        directory=f"{direktori_skrip}/frontend/assets"
    ), 
    name="assets"
)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

app.include_router(backend.run)
app.include_router(frontend.run)

if __name__ == "__main__":
    uvicorn.run("main:app", host='0.0.0.0', port=2606, reload=True) # nosec
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import pydatabase, pytable, auth

import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # --- DIJALANKAN SAAT STARTUP ---
    print("Aplikasi sedang berjalan...")

    # Aplikasi mulai menerima request setelah ini
    yield
    
    # --- DIJALANKAN SAAT SHUTDOWN ---
    print("Aplikasi sedang dimatikan...")
    
# PENTING: Tambahkan root_path agar sinkron dengan Nginx /thorix/
app = FastAPI(root_path="/thorix", lifespan=lifespan) 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["DELETE", "GET", "POST", "PUT", "PATCH"],
    allow_headers=["*"],
)


# Root route untuk testing apakah aplikasi sudah "up"
@app.get("/")
def read_root():
    return {"status": "FastAPI is running", "path": "/thorix/"}

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

app.include_router(pydatabase.router)
app.include_router(pytable.router)
app.include_router(auth.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host='0.0.0.0', port=2606, reload=True) # nosec
import os
import tempfile
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

os.environ["WHISPER_CACHE_DIR"] = "/tmp/whisper-cache"
os.environ["HF_HOME"] = "/tmp/huggingface"
os.environ["HF_HUB_CACHE"] = "/tmp/huggingface/hub"
os.environ["XDG_CACHE_HOME"] = "/tmp/.cache"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whisper-api")

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info("Loading faster-whisper tiny.en model (INT8)...")
    t0 = time.time()
    from faster_whisper import WhisperModel
    model = WhisperModel(
        "tiny.en",
        device="cpu",
        compute_type="int8",
        cpu_threads=1,
        num_workers=1,
        download_root="/tmp/whisper-cache",
    )
    logger.info(f"Model loaded in {time.time() - t0:.1f}s")
    yield
    model = None

app = FastAPI(
    title="Whisper ASR API",
    description="faster-whisper tiny.en on Render free tier",
    version="1.0.0",
    lifespan=lifespan,
)

class TranscriptionResponse(BaseModel):
    text: str
    duration_seconds: float
    language: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model: str = "tiny.en"

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=model is not None,
    )

@app.get("/")
async def root():
    return {"message": "Whisper ASR API is running", "model": "tiny.en", "docs": "/docs"}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    ext = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:
            os.unlink(tmp.name)
            raise HTTPException(status_code=413, detail="File too large (max 25MB)")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        t0 = time.time()
        segments, info = model.transcribe(tmp_path, beam_size=1, language="en")
        text = " ".join(seg.text.strip() for seg in segments)
        elapsed = time.time() - t0
        logger.info(f"Transcribed {len(content)} bytes in {elapsed:.1f}s")
        return TranscriptionResponse(
            text=text,
            duration_seconds=round(elapsed, 2),
            language=info.language,
        )
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

import os
import uuid
import struct
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()

# Folder initialization
STATIC_DIR = "static"
AUDIO_DIR = os.path.join(STATIC_DIR, "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="templates")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def to_wav(audio_bytes: bytes) -> bytes:
    data_size = len(audio_bytes)
    # 24kHz Mono PCM header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ",
        16, 1, 1, 24000, 48000, 2, 16, b"data", data_size
    )
    return header + audio_bytes

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")
        
        # 1. Credit Check logic (Add Firebase check here)
        
        if not text:
            raise HTTPException(status_code=400, detail="டெக்ஸ்ட் காலியாக உள்ளது!")

        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )
        )

        audio_bytes = b""
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=config
        ):
            if chunk.parts:
                for part in chunk.parts:
                    if part.inline_data:
                        audio_bytes += part.inline_data.data

        # 2. Save file
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_bytes))

        # 3. Credit Deduction logic (Firebase Increment(-len(text)))

        return {"status": "success", "audio_url": f"/static/audio_cache/{filename}"}

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

import os
import uuid
import struct
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()

# Folders
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 10 மொழிகள் மற்றும் 26 குரல்கள் (Gemini TTS-க்கு ஏற்றது)
LANGUAGES = {
    "ta-IN": "Tamil", "en-US": "English (US)", "en-IN": "English (India)",
    "hi-IN": "Hindi", "te-IN": "Telugu", "kn-IN": "Kannada", 
    "ml-IN": "Malayalam", "mr-IN": "Marathi", "bn-IN": "Bengali", "gu-IN": "Gujarati"
}

VOICES = [
    "Aoede", "Charon", "Fenrir", "Kore", "Puck", "Rheia", "Atreus", "Triton", 
    "Cyllene", "Leda", "Calliope", "Orpheus", "Hestia", "Hermes", "Ganymede", 
    "Pan", "Eirene", "Daphne", "Io", "Metis", "Thebe", "Ananke", "Carme", 
    "Pasiphae", "Sinope", "Lysithea"
]

def to_wav(audio_bytes: bytes) -> bytes:
    data_size = len(audio_bytes)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ",
        16, 1, 1, 24000, 48000, 2, 16, b"data", data_size
    )
    return header + audio_bytes

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "languages": LANGUAGES, "voices": VOICES}
    )

@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")
        # உணர்ச்சிகளைச் சேர்க்க 'prompt' வசதி
        user_prompt = data.get("prompt", "Say this in a natural way") 

        if not text:
            return JSONResponse({"status": "error", "message": "Text is empty"}, status_code=400)

        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )
        )

        audio_bytes = b""
        # நீங்கள் கேட்ட gemini-2.5-flash-preview-tts மாடல்
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash-preview-tts",
            contents=text, # இங்கே நீங்கள் Prompt-ஐயும் இணைக்கலாம்: contents=[user_prompt, text]
            config=config
        ):
            if chunk.parts:
                for part in chunk.parts:
                    if part.inline_data:
                        audio_bytes += part.inline_data.data

        if not audio_bytes:
            return JSONResponse({"status": "error", "message": "Audio generation failed"}, status_code=500)

        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_bytes))

        return {"status": "success", "audio_url": f"/static/{filename}"}

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

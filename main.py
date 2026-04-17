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

# ஆடியோ கோப்புகளை சேமிக்க 'static' ஃபோல்டர்
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client (உங்கள் API KEY-ஐ Render Environment Variables-ல் சேர்க்கவும்)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# புதிய மாடல் ஐடி (Notebook-ல் உள்ளபடி)
MODEL_ID = "gemini-3.1-flash-tts-preview"

LANGUAGES = {
    "ta-IN": "Tamil", "hi-IN": "Hindi", "en-US": "English (US)", "te-IN": "Telugu"
}

VOICES = ["Aoede", "Charon", "Fenrir", "Kore", "Puck", "Rheia", "Atreus", "Triton"]

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
    # இதில்தான் தவறு இருந்தது, இப்போது சரி செய்யப்பட்டுள்ளது
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "languages": LANGUAGES, 
        "voices": VOICES
    })

@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "Puck")
        speed = data.get("speed", "normal") # வேகம்

        if not text:
            return JSONResponse({"status": "error", "message": "Text is empty"}, status_code=400)

        # டைரக்டர் நோட்ஸ் மூலம் வேகத்தை கட்டுப்படுத்துதல்
        prompt = f"Director's Note: Speak at a {speed} pace. Transcript: {text}"

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )
        )

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=config
        )

        audio_part = response.candidates[0].content.parts[0]
        if not audio_part.inline_data:
             return JSONResponse({"status": "error", "message": "No audio generated"}, status_code=500)

        audio_bytes = audio_part.inline_data.data
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)
        
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_bytes))

        return {"status": "success", "audio_url": f"/static/{filename}"}

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

import os
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from google import genai
from google.genai import types

# =========================
# APP INIT
# =========================
app = FastAPI()

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# =========================
# GEMINI CLIENT
# =========================
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# =========================
# VOICES (26)
# =========================
VOICES = [
    "Puck","Kore","Aoede","Charon","Fenrir","Gacrux","Iapetus","Leda",
    "Orus","Zephyr","Achernar","Algieba","Alnilam","Autonoe","Callirrhoe",
    "Despina","Enceladus","Erinome","Laomedeia","Pulcherrima","Rasalgethi",
    "Sadachbia","Sadaltager","Sulafat","Achird","Algenib"
]

# =========================
# LANGUAGES (10)
# =========================
LANGUAGES = {
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "pa": "Punjabi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "en": "English"
}

# =========================
# HOME
# =========================
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voices": VOICES,
        "languages": LANGUAGES
    })

# =========================
# GET DATA
# =========================
@app.get("/voices")
async def voices():
    return {"voices": VOICES}

@app.get("/languages")
async def languages():
    return {"languages": LANGUAGES}

# =========================
# GENERATE AUDIO (TTS)
# =========================
@app.post("/generate")
async def generate(request: Request):

    try:
        data = await request.json()

        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")
        language = data.get("language", "en")

        if not text:
            return JSONResponse({"error": "Empty text"}, 400)

        if voice not in VOICES:
            voice = "Aoede"

        if language not in LANGUAGES:
            language = "en"

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                )
            )
        )

        audio = b""
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                audio += part.inline_data.data

        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)

        with open(filepath, "wb") as f:
            f.write(audio)

        return {
            "status": "success",
            "audio_url": f"/static/{filename}",
            "voice": voice,
            "language": language
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

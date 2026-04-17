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
# GEMINI CLIENT SAFE INIT
# =========================
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ GEMINI_API_KEY missing!")

client = genai.Client(api_key=API_KEY)

# =========================
# VOICES & LANGUAGES
# =========================
VOICES = [
    'Puck','Kore','Algenib','Zephyr','Achernar','Achird','Algieba','Alnilam',
    'Aoede','Autonoe','Callirrhoe','Charon','Despina','Enceladus','Erinome',
    'Fenrir','Gacrux','Iapetus','Laomedeia','Leda','Orus','Pulcherrima',
    'Rasalgethi','Sadachbia','Sadaltager','Sulafat'
]

LANGUAGES = {
    'ta':'Tamil','hi':'Hindi','te':'Telugu','kn':'Kannada','ml':'Malayalam',
    'mr':'Marathi','pa':'Punjabi','bn':'Bengali','gu':'Gujarati','en':'English'
}

# =========================
# HOME PAGE
# =========================
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# =========================
# VOICES LIST
# =========================
@app.get("/voices")
async def voices():
    return {"voices": VOICES}

# =========================
# LANGUAGES LIST
# =========================
@app.get("/languages")
async def languages():
    return {"languages": LANGUAGES}

# =========================
# GENERATE AUDIO (SAFE)
# =========================
@app.post("/generate")
async def generate(request: Request):

    try:
        data = await request.json()

        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")
        language = data.get("language", "en")

        # -------------------------
        # VALIDATION
        # -------------------------
        if not text:
            return JSONResponse({"status": "error", "message": "Empty text"}, status_code=400)

        if voice not in VOICES:
            voice = "Aoede"

        if language not in LANGUAGES:
            language = "en"

        if not API_KEY:
            return JSONResponse({"status": "error", "message": "API key missing"}, status_code=500)

        # -------------------------
        # GEMINI TTS CALL
        # -------------------------
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

        # -------------------------
        # AUDIO EXTRACTION SAFE
        # -------------------------
        audio_bytes = b""

        if not response or not response.candidates:
            return JSONResponse({"status": "error", "message": "No response"}, 500)

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                audio_bytes += part.inline_data.data

        if not audio_bytes:
            return JSONResponse({"status": "error", "message": "No audio returned"}, 500)

        # -------------------------
        # SAVE FILE
        # -------------------------
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)

        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        return {
            "status": "success",
            "audio_url": f"/static/{filename}",
            "voice": voice,
            "language": language
        }

    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

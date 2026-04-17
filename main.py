import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
# =========================
# 10 LANGUAGES
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
# 26 VOICES
# =========================
VOICES = [
    "Puck","Kore","Aoede","Charon","Fenrir","Gacrux","Iapetus","Leda",
    "Orus","Zephyr","Achernar","Algieba","Alnilam","Autonoe","Callirrhoe",
    "Despina","Enceladus","Erinome","Laomedeia","Pulcherrima","Rasalgethi",
    "Sadachbia","Sadaltager","Sulafat","Achird","Algenib"
]

# =========================
# FRONTEND PAGE
# =========================
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "languages": LANGUAGES,
        "voices": VOICES
    })

# =========================
# GENERATE AUDIO API
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

        if not response or not response.candidates:
            return JSONResponse({"error": "No response"}, 500)

        audio = b""

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                audio += part.inline_data.data

        filename = f"{uuid.uuid4()}.wav"
        path = os.path.join("static", filename)

        with open(path, "wb") as f:
            f.write(audio)

        return {
            "status": "success",
            "audio_url": f"/static/{filename}"
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

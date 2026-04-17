import os
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from google import genai
from google.genai import types

app = FastAPI()

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# 🔥 SAFE API CHECK
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ GEMINI_API_KEY NOT SET")

client = genai.Client(api_key=API_KEY)

LANGUAGES = {
    "ta": "Tamil","hi": "Hindi","te": "Telugu","kn": "Kannada",
    "ml": "Malayalam","mr": "Marathi","pa": "Punjabi",
    "bn": "Bengali","gu": "Gujarati","en": "English"
}

VOICES = [
    "Puck","Kore","Aoede","Charon","Fenrir","Gacrux","Iapetus","Leda",
    "Orus","Zephyr","Achernar","Algieba","Alnilam","Autonoe","Callirrhoe",
    "Despina","Enceladus","Erinome","Laomedeia","Pulcherrima","Rasalgethi",
    "Sadachbia","Sadaltager","Sulafat","Achird","Algenib"
]

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voices": VOICES,
        "languages": LANGUAGES
    })

@app.post("/generate")
async def generate(request: Request):

    try:
        data = await request.json()

        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")
        language = data.get("language", "en")

        if not text:
            return JSONResponse({"error": "Empty text"}, 400)

        if not API_KEY:
            return JSONResponse({"error": "API key missing"}, 500)

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

        # 🔥 SAFE CHECK (IMPORTANT FIX)
        if not response or not response.candidates:
            return JSONResponse({"error": "No response from AI"}, 500)

        audio = b""

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                audio += part.inline_data.data

        if not audio:
            return JSONResponse({"error": "No audio generated"}, 500)

        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)

        with open(filepath, "wb") as f:
            f.write(audio)

        return {
            "status": "success",
            "audio_url": f"/static/{filename}"
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

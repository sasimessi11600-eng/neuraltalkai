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

# static ஃபோல்டர் செட்டப்
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# டேட்டா செட்டப்
LANGUAGES = {"ta": "Tamil", "en": "English", "hi": "Hindi"}
VOICES = ["Aoede", "Puck", "Charon", "Kore", "Rheia"]

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
    # லாக்-ல் இருந்த பிழை இங்கே சரிசெய்யப்பட்டது
    context = {
        "request": request,
        "languages": LANGUAGES,
        "voices": VOICES
    }
    return templates.TemplateResponse("index.html", context)

@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")

        if not text:
            return JSONResponse({"status": "error", "message": "Text is empty"}, status_code=400)

        # Gemini 2.5 TTS மாடல்
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )

        audio_bytes = b""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    audio_bytes += part.inline_data.data

        if not audio_bytes:
            return JSONResponse({"status": "error", "message": "No audio returned"}, status_code=500)

        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_bytes))

        return {"status": "success", "audio_url": f"/static/{filename}"}

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

os.makedirs("audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None


class TTSRequest(BaseModel):
    text: str
    voice: str = "Kore"
    style: str = "Speak naturally"


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/generate")
def generate(req: TTSRequest):
    if client is None:
        raise HTTPException(status_code=500, detail="Missing GEMINI_API_KEY")

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text required")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=f"{req.style}: {req.text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=req.voice
                        )
                    )
                )
            )
        )

        audio_bytes = response.candidates[0].content.parts[0].inline_data.data

        if not audio_bytes:
            raise Exception("No audio returned")

        filename = f"{uuid.uuid4()}.wav"
        filepath = f"audio/{filename}"

        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        return {"file": f"/audio/{filename}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audio/{name}")
def audio(name: str):
    path = f"audio/{name}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(path, media_type="audio/wav", filename=name)

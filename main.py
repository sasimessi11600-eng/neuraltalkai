import os, uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
templates = Jinja2Templates(directory="templates")

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None


class TTSRequest(BaseModel):
    text: str
    voice: str = "Kore"
    style: str = "Speak naturally"


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
def generate(req: TTSRequest):
    if client is None:
        raise HTTPException(500, "Missing GEMINI_API_KEY")

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

        data = response.candidates[0].content.parts[0].inline_data.data
        filename = f"{uuid.uuid4()}.wav"
        path = f"audio/{filename}"

        with open(path, "wb") as f:
            f.write(data)

        return {"file": f"/audio/{filename}"}

    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/audio/{name}")
def audio(name: str):
    path = f"audio/{name}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")

    return FileResponse(path, media_type="audio/wav", filename=name)

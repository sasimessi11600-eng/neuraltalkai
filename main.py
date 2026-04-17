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
os.makedirs("templates", exist_ok=True)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Gemini Client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Convert raw PCM audio to WAV
def to_wav(audio_bytes: bytes) -> bytes:
    data_size = len(audio_bytes)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        24000,
        48000,
        2,
        16,
        b"data",
        data_size
    )

    return header + audio_bytes


# Home Page
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        request=request
    )


# Generate Audio
@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()

        text = data.get("text", "").strip()
        voice = data.get("voice", "Aoede")

        if not text:
            return JSONResponse(
                {"status": "error", "message": "Text is empty"},
                status_code=400
            )

        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
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
                    if part.inline_data and part.inline_data.data:
                        audio_bytes += part.inline_data.data

        if not audio_bytes:
            return JSONResponse(
                {"status": "error", "message": "No audio returned"},
                status_code=500
            )

        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join("static", filename)

        with open(filepath, "wb") as f:
            f.write(to_wav(audio_bytes))

        return {
            "status": "success",
            "audio_url": f"/static/{filename}"
        }

    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )

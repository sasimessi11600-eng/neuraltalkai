import os
import uuid
import struct
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env கோப்பிலிருந்து API Key-ஐ எடுக்க
load_dotenv()

app = FastAPI()

# ஆடியோ சேமிக்கும் போல்டரை உருவாக்குதல்
STATIC_DIR = "static"
AUDIO_DIR = os.path.join(STATIC_DIR, "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Static மற்றும் Templates செட்டப்
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client செட்டப்
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Gemini தரும் PCM ஆடியோவை WAV கோப்பாக மாற்றும் பங்க்ஷன்
def to_wav(audio_bytes: bytes) -> bytes:
    data_size = len(audio_bytes)
    # Gemini 2.5 TTS பொதுவாக 24kHz, 16-bit Mono-வில் ஆடியோ தரும்
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ",
        16, 1, 1, 24000, 48000, 2, 16, b"data", data_size
    )
    return header + audio_bytes

# முகப்பு பக்கம் (Home Page)
@app.get("/")
async def home(request: Request):
    # சரியான முறை:
return templates.TemplateResponse(
    name="index.html", 
    context={"request": request}
)
# ஆடியோ ஜெனரேட் செய்யும் மெயின் API
@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "Puck") # Default-ஆக Puck குரல்

        if not text:
            raise HTTPException(status_code=400, detail="Text is empty!")

        # Gemini 2.5 Flash Preview TTS Configuration
        model_id = "gemini-2.5-flash-preview-tts"
        
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

        audio_output = b""

        # ஸ்ட்ரீமிங் முறையில் ஆடியோவைப் பெறுதல்
        for chunk in client.models.generate_content_stream(
            model=model_id,
            contents=text,
            config=config
        ):
            if chunk.parts:
                for part in chunk.parts:
                    if part.inline_data:
                        audio_output += part.inline_data.data

        if not audio_output:
            raise HTTPException(status_code=500, detail="No audio data generated")

        # தனித்துவமான கோப்பு பெயரை உருவாக்குதல்
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # WAV கோப்பாகச் சேமித்தல்
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_output))

        return {
            "status": "success",
            "audio_url": f"/static/audio_cache/{filename}"
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# சர்வர் ரன் செய்ய (Local Testing)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

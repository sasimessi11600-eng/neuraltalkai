import os
import struct
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()

# static ஃபோல்டர் செட்டப்
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def convert_to_wav(audio_data: bytes) -> bytes:
    """Raw PCM ஆடியோவை WAV கோப்பாக மாற்றும்"""
    data_size = len(audio_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ",
        16, 1, 1, 24000, 48000, 2, 16, b"data", data_size
    )
    return header + audio_data

@app.get("/")
async def home(request: Request):
    # இங்கிருந்த பிழையை (Internal Server Error) சரிசெய்துவிட்டேன்
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate_audio(request: Request):
    try:
        data = await request.json()
        text = data.get("text")
        voice = data.get("voice", "Aoede")

        if not text:
            return JSONResponse({"status": "error", "message": "Text is empty!"}, status_code=400)

        # 2.5 மாடல் அல்லது 2.0-flash எதிலாவது ஒன்று கண்டிப்பாக வேலை செய்யும்
        # தற்போது கூகுள் பரிந்துரைக்கும் மாடல்
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
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
            return JSONResponse({"status": "error", "message": "No audio returned!"}, status_code=500)

        file_name = "output.wav"
        output_path = os.path.join("static", file_name)
        
        with open(output_path, "wb") as f:
            f.write(convert_to_wav(audio_bytes))

        return {"status": "success", "audio_url": f"/static/{file_name}?v={os.urandom(2).hex()}"}

    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

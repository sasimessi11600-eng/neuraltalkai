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
    bits_per_sample = 16
    sample_rate = 24000
    num_channels = 1
    data_size = len(audio_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ",
        16, 1, num_channels, sample_rate,
        sample_rate * 2, 2, bits_per_sample,
        b"data", data_size
    )
    return header + audio_data

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/generate")
async def generate_audio(request: Request):
    try:
        data = await request.json()
        text = data.get("text")
        voice = data.get("voice", "Aoede")

        if not text:
            return JSONResponse({"status": "error", "message": "Text is empty!"}, status_code=400)

        # Gemini 2.0 Flash-க்கு சரியான முறையில் கட்டளை அனுப்புதல்
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Please read this text aloud exactly as it is: {text}",
            config=types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )

        # ஆடியோ டேட்டாவைச் சேகரித்தல்
        audio_bytes = b""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    audio_bytes += part.inline_data.data

        if not audio_bytes:
            # ஒருவேளை ஆடியோ வரவில்லை என்றால் மாற்று வழி
            return JSONResponse({"status": "error", "message": "API did not return audio. Check your API key or Text."}, status_code=500)

        # ஆடியோவைச் சேமித்தல்
        file_name = "output.wav"
        output_path = os.path.join("static", file_name)
        
        final_audio = convert_to_wav(audio_bytes)
        with open(output_path, "wb") as f:
            f.write(final_audio)

        # பிரவுசரில் Cache ஆகாமல் இருக்க Random ID
        v_id = os.urandom(4).hex()
        return {
            "status": "success", 
            "audio_url": f"/static/{file_name}?v={v_id}"
        }

    except Exception as e:
        # எரர் மெசேஜை தெளிவாகப் பார்க்க
        print(f"Server Error: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

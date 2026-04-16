import os
import struct
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()

# static ஃபோல்டர் உருவாக்குதல்
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client செட்டப்
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def convert_to_wav(audio_data: bytes) -> bytes:
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
            return {"status": "error", "message": "Text is empty!"}

        # Gemini TTS - ஆடியோ உருவாக்கம்
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )

        audio_bytes = b""
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                audio_bytes += part.inline_data.data

        # ஆடியோவைச் சேமித்தல்
        file_name = "output.wav"
        output_path = os.path.join("static", file_name)
        
        final_audio = convert_to_wav(audio_bytes)
        with open(output_path, "wb") as f:
            f.write(final_audio)

        return {
            "status": "success", 
            "audio_url": f"/static/{file_name}?v={os.urandom(4).hex()}" # Cache ஆகாமல் இருக்க சின்ன ட்ரிக்
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

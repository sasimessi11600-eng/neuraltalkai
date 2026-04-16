import os
import struct
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()

# ஆடியோ கோப்புகளைச் சேமிக்க 'static' ஃபோல்டர் தேவை
if not os.path.exists("static"):
    os.makedirs("static")

# Static மற்றும் Templates செட்டப்
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client செட்டப் (Render-ல் GEMINI_API_KEY செட் செய்திருக்க வேண்டும்)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def convert_to_wav(audio_data: bytes) -> bytes:
    """Raw ஆடியோவை பிரவுசரில் பிளே செய்யக்கூடிய WAV கோப்பாக மாற்றும்"""
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

# --- ROUTES ---

@app.get("/")
async def home(request: Request):
    """ஹோம் பேஜை காண்பிக்கும்"""
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/generate")
async def generate_audio(request: Request):
    try:
        data = await request.json()
        text = data.get("text")
        voice = data.get("voice", "Aoede") # டீஃபால்ட் வாய்ஸ் Aoede

        if not text:
            return JSONResponse({"status": "error", "message": "Text is required!"}, status_code=400)

        # 1. Gemini 2.0 Flash பயன்படுத்தி ஆடியோ உருவாக்கம்
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

        # 2. அவுட்புட் ஆடியோ டேட்டாவை எடுத்தல்
        audio_bytes = b""
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                audio_bytes += part.inline_data.data

        if not audio_bytes:
            return JSONResponse({"status": "error", "message": "No audio generated from Gemini"}, status_code=500)

        # 3. ஆடியோவை WAV கோப்பாகச் சேமித்தல்
        file_name = "output.wav"
        output_path = os.path.join("static", file_name)
        
        final_audio = convert_to_wav(audio_bytes)
        with open(output_path, "wb") as f:
            f.write(final_audio)

        # 4. ஆடியோ URL-ஐ பதிலுக்காக அனுப்புதல்
        # Cache எரர் வராமல் இருக்க ஒவ்வொரு முறை புதிய ID சேர்க்கப்படுகிறது (?v=...)
        v_param = os.urandom(4).hex()
        return {
            "status": "success", 
            "audio_url": f"/static/{file_name}?v={v_param}"
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Render போர்ட் செட்டிங்ஸ்
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

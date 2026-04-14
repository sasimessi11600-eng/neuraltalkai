import os
import struct
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore

app = FastAPI()

# 1. CORS அனுமதி (Vercel Frontend-க்காக)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ஸ்டாட்டிக் மற்றும் டெம்ப்ளேட் செட்டப்
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 2. Firebase பாதுகாப்பு செட்டப்
# Local-ல் இருந்தால் ஃபைலை எடுக்கும், Render-ல் இருந்தால் Environment Variable-ஐ எடுக்கும்
try:
    if os.path.exists("firebase_key.json"):
        cred = credentials.Certificate("firebase_key.json")
    else:
        fb_config = os.environ.get("FIREBASE_CONFIG")
        if fb_config:
            cred = credentials.Certificate(json.loads(fb_config))
        else:
            print("எச்சரிக்கை: Firebase Config காணப்படவில்லை!")
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Firebase Setup Error: {e}")

# 3. Gemini API Key (GitHub-ல் தெரியாது, Render-ல் செட் செய்ய வேண்டும்)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def convert_to_wav(audio_data: bytes) -> bytes:
    """Raw ஆடியோவை WAV கோப்பாக மாற்றும்"""
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
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate_audio(request: Request):
    try:
        data = await request.json()
        user_email = data.get("email")
        text = data.get("text")
        voice = data.get("voice", "Aoede")
        
        if not user_email or not text:
            raise HTTPException(status_code=400, detail="Email and Text are required!")

        # A. கிரெடிட் செக்
        user_ref = db.collection("users").document(user_email)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found in Firebase!")
            
        current_credits = user_doc.to_dict().get("credits", 0)
        if current_credits < len(text):
            raise HTTPException(status_code=400, detail="Insufficient credits!")

        # B. Gemini TTS உருவாக்கம்
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
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

        # C. ஆடியோவைச் சேமித்தல்
        file_id = user_email.split('@')[0]
        file_name = f"output_{file_id}.wav"
        output_path = os.path.join("static", file_name)
        
        final_audio = convert_to_wav(audio_bytes)
        with open(output_path, "wb") as f:
            f.write(final_audio)

        # D. கிரெடிட் அப்டேட்
        new_credits = current_credits - len(text)
        user_ref.update({"credits": new_credits})

        # ஆடியோ URL-ஐ உருவாக்குதல்
        protocol = "https" if "render" in request.base_url.hostname else "http"
        base_url = f"{protocol}://{request.base_url.hostname}"
        if request.base_url.port and protocol == "http":
            base_url += f":{request.base_url.port}"
            
        return {
            "status": "success", 
            "audio_url": f"{base_url}/static/{file_name}",
            "remaining_credits": new_credits
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Render-ல் PORT-ஐ தானாக எடுக்கும்
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
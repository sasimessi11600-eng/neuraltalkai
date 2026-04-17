import os
import uuid
import struct
import json
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- 🛡️ Firebase Setup (Environment Variable மூலம்) ---
try:
    # Render-ன் 'Environment Variables' செக்ஷனில் 'FIREBASE_CONFIG' என்ற பெயரில் 
    # உங்கள் முழு JSON-ஐயும் பேஸ்ட் செய்ய வேண்டும்.
    firebase_json = os.getenv("FIREBASE_CONFIG")
    
    if firebase_json:
        # JSON ஸ்ட்ரிங்கை டிட்க்ஷனரியாக மாற்றி Firebase-ஐ துவங்குதல்
        firebase_info = json.loads(firebase_json)
        cred = credentials.Certificate(firebase_info)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase successfully initialized from Environment Variable!")
    else:
        print("Error: FIREBASE_CONFIG Environment Variable not found!")
except Exception as e:
    print(f"Firebase Init Error: {e}")

# Static & Templates setup
STATIC_DIR = "static"
AUDIO_DIR = os.path.join(STATIC_DIR, "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={}
    )

@app.post("/generate")
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "puck") # Gemini-ன் நவீன குரல்
        user_id = data.get("user_id", "test_user") # உங்கள் டேட்டாபேஸில் உள்ள User ID

        if not text:
            raise HTTPException(status_code=400, detail="Text is empty")

        # --- 💰 கிரெடிட் செக் ---
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return JSONResponse({"status": "error", "message": "User not found!"}, status_code=404)

        current_credits = user_doc.to_dict().get("credits", 0)
        cost = 100

        if current_credits < cost:
            return JSONResponse({
                "status": "error", 
                "message": f"போதிய கிரெடிட்கள் இல்லை! பேலன்ஸ்: {current_credits}"
            }, status_code=402)

        # --- 🎙️ Gemini 2.5 Flash Preview TTS ---
        model_id = "gemini-2.5-flash-preview-tts"
        config = types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )
        )

        audio_output = b""
        for chunk in client.models.generate_content_stream(model=model_id, contents=text, config=config):
            if chunk.parts:
                for part in chunk.parts:
                    if part.inline_data:
                        audio_output += part.inline_data.data

        if not audio_output:
            raise HTTPException(status_code=500, detail="Audio generation failed")

        # கிரெடிட் குறைத்தல் (Success-க்கு பிறகு)
        user_ref.update({"credits": firestore.Increment(-cost)})

        # கோப்பாகச் சேமித்தல்
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_output))

        return {
            "status": "success",
            "audio_url": f"/static/audio_cache/{filename}"
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

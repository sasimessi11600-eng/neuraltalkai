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

# .env கோப்பை லோடு செய்ய
load_dotenv()

app = FastAPI()

# --- 🛡️ Firebase Setup (சரியான முறை) ---
db = None

try:
    # Render-ன் Environment Variables-ல் நாம் கொடுத்த JSON-ஐ எடுக்கும்
    firebase_json = os.getenv("FIREBASE_CONFIG")
    
    if firebase_json:
        firebase_info = json.loads(firebase_json)
        
        # ஏற்கனவே ஒரு Firebase App ரன் ஆகிக்கொண்டிருந்தால் அதை மீண்டும் துவக்காமல் இருக்க இந்த செக்
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_info)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        print("✅ Firebase successfully initialized!")
    else:
        print("❌ Error: FIREBASE_CONFIG Environment Variable not found!")
except Exception as e:
    print(f"❌ Firebase Init Error: {e}")

# Static & Templates setup
STATIC_DIR = "static"
AUDIO_DIR = os.path.join(STATIC_DIR, "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Audio header conversion function
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
    # 'request' ஆர்குமெண்ட் சரியாக அனுப்பப்படுவதை உறுதி செய்கிறோம்
    return templates.TemplateResponse(
        name="index.html", 
        context={"request": request}
    )

@app.post("/generate")
async def generate(request: Request):
    try:
        # 1. 'db' சரியாக டிஃபைன் ஆகி உள்ளதா என முதலில் பார்க்க வேண்டும்
        if db is None:
            return JSONResponse({
                "status": "error", 
                "message": "டேட்டாபேஸ் இணைப்பு தோல்வியடைந்தது. FIREBASE_CONFIG-ஐச் சரிபார்க்கவும்."
            }, status_code=500)

        data = await request.json()
        text = data.get("text", "").strip()
        voice = data.get("voice", "puck") 
        user_id = data.get("user_id", "test_user")

        if not text:
            raise HTTPException(status_code=400, detail="Text is empty")

        # 2. 💰 கிரெடிட் செக் (Firestore-ல் இருந்து)
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return JSONResponse({"status": "error", "message": "User not found!"}, status_code=404)

        current_credits = user_doc.to_dict().get("credits", 0)
        cost = 100

        if current_credits < cost:
            return JSONResponse({
                "status": "error", 
                "message": f"போதிய கிரெடிட்கள் இல்லை! தற்போதைய பேலன்ஸ்: {current_credits}"
            }, status_code=402)

        # 3. 🎙️ Gemini 2.5 Flash TTS Generation
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

        # 4. 📉 கிரெடிட் குறைத்தல் மற்றும் புதுப்பித்தல்
        new_credits = current_credits - cost
        user_ref.update({"credits": new_credits})

        # 5. ஆடியோ கோப்பைச் சேமித்தல்
        filename = f"{uuid.uuid4()}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(to_wav(audio_output))

        return {
            "status": "success",
            "audio_url": f"/static/audio_cache/{filename}",
            "remaining_credits": new_credits
        }

    except Exception as e:
        print(f"Generate Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

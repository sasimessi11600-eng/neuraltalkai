import os
import uuid
import wave
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

import firebase_admin
from firebase_admin import credentials, auth, firestore

# -------------------------
# Firebase Init
# -------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------
# FastAPI Init
# -------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

os.makedirs("audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------
# Gemini API
# -------------------------
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

# -------------------------
# Models
# -------------------------
class SignupModel(BaseModel):
    email: str
    password: str

class LoginModel(BaseModel):
    email: str
    password: str

class BuyModel(BaseModel):
    uid: str
    amount: int

class TTSRequest(BaseModel):
    uid: str
    text: str
    voice: str = "Kore"
    style: str = "Speak naturally"

# -------------------------
# Pages
# -------------------------
@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/dashboard.html")

# -------------------------
# Signup
# -------------------------
@app.post("/signup")
def signup(data: SignupModel):
    try:
        user = auth.create_user(
            email=data.email,
            password=data.password
        )

        db.collection("users").document(user.uid).set({
            "email": data.email,
            "credits": 0,
            "used_chars": 0,
            "plan": "none"
        })

        return {"success": True, "uid": user.uid}

    except Exception as e:
        raise HTTPException(400, str(e))

# -------------------------
# Login Demo
# -------------------------
@app.post("/login")
def login(data: LoginModel):
    docs = db.collection("users").where("email", "==", data.email).stream()

    for doc in docs:
        return {"success": True, "uid": doc.id}

    raise HTTPException(401, "User not found")

# -------------------------
# Get User Info
# -------------------------
@app.get("/me/{uid}")
def me(uid: str):
    doc = db.collection("users").document(uid).get()

    if not doc.exists:
        raise HTTPException(404, "User not found")

    return doc.to_dict()

# -------------------------
# Demo Buy Credits
# -------------------------
@app.post("/buy-demo")
def buy_demo(data: BuyModel):
    plans = {
        149: (35000, "Starter"),
        299: (80000, "Pro"),
        599: (170000, "Business")
    }

    if data.amount not in plans:
        raise HTTPException(400, "Invalid plan")

    add_chars, plan_name = plans[data.amount]

    ref = db.collection("users").document(data.uid)
    user = ref.get().to_dict()

    new_credits = user["credits"] + add_chars

    ref.update({
        "credits": new_credits,
        "plan": plan_name
    })

    return {
        "success": True,
        "credits": new_credits,
        "plan": plan_name
    }

# -------------------------
# Generate TTS
# -------------------------
@app.post("/generate")
def generate(req: TTSRequest):
    if client is None:
        raise HTTPException(500, "Missing GEMINI_API_KEY")

    ref = db.collection("users").document(req.uid)
    doc = ref.get()

    if not doc.exists:
        raise HTTPException(404, "User not found")

    user = doc.to_dict()
    chars = len(req.text)

    if user["credits"] < chars:
        raise HTTPException(400, "Insufficient credits")

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

        pcm_data = response.candidates[0].content.parts[0].inline_data.data

        filename = f"{uuid.uuid4()}.wav"
        filepath = f"audio/{filename}"

        with wave.open(filepath, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(pcm_data)

        ref.update({
            "credits": user["credits"] - chars,
            "used_chars": user["used_chars"] + chars
        })

        return {
            "success": True,
            "file": f"/audio/{filename}"
        }

    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------
# Audio
# -------------------------
@app.get("/audio/{name}")
def audio(name: str):
    path = f"audio/{name}"

    if not os.path.exists(path):
        raise HTTPException(404, "Not found")

    return FileResponse(path, media_type="audio/wav", filename=name)

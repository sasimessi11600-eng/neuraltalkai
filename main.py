import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# 🔥 10 LANGUAGES
LANGUAGES = {
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "pa": "Punjabi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "en": "English"
}

# 🔥 26 VOICES
VOICES = [
    "Puck","Kore","Aoede","Charon","Fenrir","Gacrux","Iapetus","Leda",
    "Orus","Zephyr","Achernar","Algieba","Alnilam","Autonoe","Callirrhoe",
    "Despina","Enceladus","Erinome","Laomedeia","Pulcherrima","Rasalgethi",
    "Sadachbia","Sadaltager","Sulafat","Achird","Algenib"
]

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "languages": LANGUAGES,
        "voices": VOICES
    })

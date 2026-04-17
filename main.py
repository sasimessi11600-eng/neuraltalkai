import os, uuid, struct
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')
client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

VOICES = ['Puck','Kore','Algenib','Zephyr','Achernar','Achird','Algieba','Alnilam','Aoede','Autonoe','Callirrhoe','Charon','Despina','Enceladus','Erinome','Fenrir','Gacrux','Iapetus','Laomedeia','Leda','Orus','Pulcherrima','Rasalgethi','Sadachbia','Sadaltager','Sulafat']
LANGUAGES = {
 'ta':'Tamil','hi':'Hindi','te':'Telugu','kn':'Kannada','ml':'Malayalam',
 'mr':'Marathi','pa':'Punjabi','bn':'Bengali','gu':'Gujarati','en':'English'
}

def to_wav(audio: bytes):
    return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF',36+len(audio),b'WAVE',b'fmt ',16,1,1,24000,48000,2,16,b'data',len(audio))+audio

@app.get('/')
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get('/voices')
async def voices():
    return {'voices': VOICES}

@app.get('/languages')
async def languages():
    return {'languages': LANGUAGES}

@app.post('/generate')
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get('text','').strip()
        voice = data.get('voice','Aoede')
        language = data.get('language','en')
        if voice not in VOICES:
            voice = 'Aoede'
        if language not in LANGUAGES:
            language = 'en'
        if not text:
            return JSONResponse({'status':'error','message':'Empty text'},400)
        r = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=['audio'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )
        audio=b''
        for p in r.candidates[0].content.parts:
            if p.inline_data:
                audio += p.inline_data.data
        if not audio:
            return JSONResponse({'status':'error','message':'No audio returned'},500)
        name=f'{uuid.uuid4()}.wav'
        with open(os.path.join('static',name),'wb') as f:
            f.write(to_wav(audio))
        return {'status':'success','audio_url':f'/static/{name}','voice':voice,'language':language}
    except Exception as e:
        return JSONResponse({'status':'error','message':str(e)},500)

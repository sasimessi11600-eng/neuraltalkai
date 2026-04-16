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

def wav(audio: bytes):
    return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF',36+len(audio),b'WAVE',b'fmt ',16,1,1,24000,48000,2,16,b'data',len(audio))+audio

@app.get('/')
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.post('/generate')
async def generate(request: Request):
    data = await request.json()
    text = data.get('text','').strip()
    voice = data.get('voice','Aoede')
    if not text:
        return JSONResponse({'status':'error','message':'Empty text'}, status_code=400)
    try:
        r = client.models.generate_content(model='gemini-2.5-flash-preview-tts', contents=text, config=types.GenerateContentConfig(response_modalities=['audio'], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
        b = b''
        for p in r.candidates[0].content.parts:
            if p.inline_data: b += p.inline_data.data
        name = f'{uuid.uuid4()}.wav'
        with open(os.path.join('static', name),'wb') as f: f.write(wav(b))
        return {'status':'success','audio_url':f'/static/{name}'}
    except Exception as e:
        return JSONResponse({'status':'error','message':str(e)}, status_code=500)

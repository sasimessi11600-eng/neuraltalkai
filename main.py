import os, uuid, struct
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types

app = FastAPI()
os.makedirs('static', exist_ok=True)
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

def to_wav(audio):
    size=len(audio)
    return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF',36+size,b'WAVE',b'fmt ',16,1,1,24000,48000,2,16,b'data',size)+audio

@app.get('/')
async def home(request: Request):
    return templates.TemplateResponse('index.html', context={'request': request})

@app.post('/generate')
async def generate(request: Request):
    try:
        body=await request.json()
        text=body.get('text','').strip()
        voice=body.get('voice','Aoede')
        if not text:
            return JSONResponse({'status':'error','message':'Enter text'},400)
        r=client.models.generate_content(model='gemini-2.5-flash-preview-tts',contents=text,config=types.GenerateContentConfig(response_modalities=['audio'],speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
        audio=b''
        for p in r.candidates[0].content.parts:
            if p.inline_data:
                audio += p.inline_data.data
        fn=f'{uuid.uuid4()}.wav'
        with open(os.path.join('static',fn),'wb') as f:
            f.write(to_wav(audio))
        return {'status':'success','audio_url':f'/static/{fn}'}
    except Exception as e:
        return JSONResponse({'status':'error','message':str(e)},500)

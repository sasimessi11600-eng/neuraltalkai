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

def wav(audio: bytes):
    size=len(audio)
    return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF',36+size,b'WAVE',b'fmt ',16,1,1,24000,48000,2,16,b'data',size)+audio

@app.get('/')
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.post('/generate')
async def generate(request: Request):
    try:
        data = await request.json()
        text = data.get('text','').strip()
        voice = data.get('voice','Aoede')
        if not text:
            return JSONResponse({'status':'error','message':'Empty text'}, status_code=400)

        config = types.GenerateContentConfig(
            response_modalities=['audio'],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            )
        )

        audio = b''
        for chunk in client.models.generate_content_stream(
            model='gemini-2.5-flash-preview-tts',
            contents=text,
            config=config
        ):
            if chunk.parts:
                for part in chunk.parts:
                    if part.inline_data and part.inline_data.data:
                        audio += part.inline_data.data

        if not audio:
            return JSONResponse({'status':'error','message':'No audio returned'}, status_code=500)

        name = f'{uuid.uuid4()}.wav'
        with open(os.path.join('static', name), 'wb') as f:
            f.write(wav(audio))

        return {'status':'success','audio_url':f'/static/{name}'}

    except Exception as e:
        return JSONResponse({'status':'error','message':str(e)}, status_code=500)

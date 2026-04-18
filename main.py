    import os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
app.mount('/static', StaticFiles(directory='static'), name='static')
os.makedirs('audio', exist_ok=True)
os.makedirs('static', exist_ok=True)

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

class TTSRequest(BaseModel):
    text:str
    voice:str='Kore'
    style:str='Speak naturally'

@app.get('/')
def home():
    return FileResponse('static/index.html')

@app.post('/generate')
def generate(req:TTSRequest):
    try:
        prompt = f"{req.style}: {req.text}"
        r = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=req.voice)
                    )
                )
            )
        )
        data = r.candidates[0].content.parts[0].inline_data.data
        name = f"{uuid.uuid4()}.wav"
        path = f'audio/{name}'
        with open(path,'wb') as f:
            f.write(data)
        return {'success':True,'file':f'/audio/{name}'}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get('/audio/{name}')
def audio(name:str):
    path = f'audio/{name}'
    if not os.path.exists(path):
        raise HTTPException(404,'Not found')
    return FileResponse(path, media_type='audio/wav', filename=name)

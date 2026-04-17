import os
import json
import base64
import hashlib
import hmac
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore, storage as fb_storage, auth as fb_auth
from google.cloud import texttospeech
from google.oauth2 import service_account

import razorpay

load_dotenv()

# ---- Config / Env ----
FIREBASE_SA_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")  # JSON string
GOOGLE_SA_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")  # JSON string
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")  # e.g. "your-project.appspot.com"

if not FIREBASE_SA_JSON or not GOOGLE_SA_JSON:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON and GOOGLE_APPLICATION_CREDENTIALS_JSON are required in env")

# ---- Init Firebase ----
fb_sa_info = json.loads(FIREBASE_SA_JSON)
fb_cred = credentials.Certificate(fb_sa_info)
firebase_admin.initialize_app(fb_cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
db = firestore.client()
bucket = fb_storage.bucket()

# ---- Init Google TTS client from service account info (no temp file) ----
g_sa_info = json.loads(GOOGLE_SA_JSON)
g_creds = service_account.Credentials.from_service_account_info(g_sa_info)
tts_client = texttospeech.TextToSpeechClient(credentials=g_creds)

# ---- Init Razorpay client ----
if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
    razorpay_client = None
else:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

app = FastAPI(title="NeuralTalk AI - Backend")

# ---- Schemas ----
class TTSRequest(BaseModel):
    email: str
    text: str
    voice_name: str
    language_code: str

# ---- Moderation stub (replace with proper pipeline) ----
def moderate_text(text: str) -> bool:
    # Return True if allowed. Extend with ML/blocklist/regex.
    blocked_terms = ["bomb", "terror", "illegal"]
    lower = text.lower()
    for t in blocked_terms:
        if t in lower:
            return False
    return True

# ---- Helpers ----
def synthesize_to_mp3_bytes(text: str, voice_name: str, language_code: str) -> bytes:
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content  # bytes

def upload_audio_to_storage(bucket_path: str, audio_bytes: bytes, content_type: str = "audio/mpeg") -> str:
    blob = bucket.blob(bucket_path)
    blob.upload_from_string(audio_bytes, content_type=content_type)
    # make signed url valid for limited time (e.g., 7 days * 24h * 360s)
    url = blob.generate_signed_url(expiration=7 * 24 * 360)
    return url

# ---- Background task ----
def background_synthesize_and_save(email: str, text: str, voice_name: str, language_code: str, job_doc_ref_path: str):
    try:
        # synthesize
        audio_bytes = synthesize_to_mp3_bytes(text, voice_name, language_code)
        # store in firebase storage under user path
        import uuid
        fname = f"generated/{email}/{uuid.uuid4().hex}.mp3"
        url = upload_audio_to_storage(fname, audio_bytes)
        # save metadata to job doc
        job_ref = firestore.client().document(job_doc_ref_path)
        job_ref.update({
            "status": "completed",
            "audio_url": url,
            "length_chars": len(text),
            "voice": voice_name,
            "language": language_code,
            "completed_at": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        # update job as failed
        job_ref = firestore.client().document(job_doc_ref_path)
        job_ref.update({
            "status": "failed",
            "error": str(e),
            "completed_at": firestore.SERVER_TIMESTAMP
        })

# ---- Endpoints ----
@app.post("/generate-audio")
async def generate_audio(req: TTSRequest, background_tasks: BackgroundTasks):
    # Basic moderation
    if not moderate_text(req.text):
        raise HTTPException(status_code=400, detail="Input text blocked by moderation")

    user_ref = db.collection("users").document(req.email)
    char_count = len(req.text)

    # Transaction to check and decrement credits atomically
    @firestore.transactional
    def txn_decrement(transaction, user_ref, amount):
        snap = user_ref.get(transaction=transaction)
        if not snap.exists:
            raise Exception("User not found")
        credits = snap.get("credits") or 
        if credits < amount:
            raise Exception("Insufficient credits")
        transaction.update(user_ref, {"credits": firestore.Increment(-amount)})
        # return remaining after decrement
        return credits - amount

    txn = db.transaction()
    try:
        remaining_after = txn_decrement(txn, user_ref, char_count)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # create a job doc for client to poll
    jobs_col = user_ref.collection("jobs")
    job_doc = jobs_col.document()
    job_doc.set({
        "status": "queued",
        "created_at": firestore.SERVER_TIMESTAMP,
        "length_chars": char_count,
        "voice": req.voice_name,
        "language": req.language_code
    })

    # background synth and save: pass job doc path for updates
    background_tasks.add_task(
        background_synthesize_and_save,
        req.email, req.text, req.voice_name, req.language_code, job_doc.path
    )

    return {"status": "accepted", "job_id": job_doc.id, "remaining_credits": remaining_after}

@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    if razorpay_client is None:
        raise HTTPException(status_code=500, detail="Razorpay not configured")

    payload_bytes = await request.body()
    payload_text = payload_bytes.decode("utf-8")
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not set")

    # Verify signature (razorpay utility)
    try:
        razorpay_client.utility.verify_webhook_signature(payload_text, signature, RAZORPAY_WEBHOOK_SECRET)
    except Exception:
        # Optionally compute HMAC manually as fallback
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    data = await request.json()
    event = data.get("event")

    # Extract payment entity safely
    payment_entity = (data.get("payload", {}) .get("payment", {}) .get("entity", {})) or {}
    payment_id = payment_entity.get("id")
    # Prefer a reliable mapping from payment to user: we recommend passing user email in order/notes
    email = payment_entity.get("email") or payment_entity.get("notes", {}).get("email")

    payments_col = db.collection("payments")
    if payment_id:
        # Idempotency: if already processed, skip
        existing = payments_col.document(payment_id).get()
        if existing.exists and existing.get("processed", False):
            return {"status": "already_processed"}

    # Log the webhook payload
    log_doc = payments_col.document(payment_id or firestore.client().collection("payments").document().id)
    log_doc.set({
        "raw": data,
        "event": event,
        "created_at": firestore.SERVER_TIMESTAMP,
        "processed": False
    })

    if event == "payment.captured":
        # Map amount -> credits (example: 1 credit per ₹1)
        amount = payment_entity.get("amount", )  # paise
        credits_to_add = int(amount // 100)  # 1 credit per ₹1
        if not email:
            # If no email is provided, mark and require manual reconciliation
            log_doc.update({"processed": False, "error": "no_email_attached"})
            return {"status": "no_email_attached"}
        user_ref = db.collection("users").document(email)
        # increment credits idempotently
        user_ref.set({"credits": firestore.Increment(credits_to_add)}, merge=True)
        log_doc.update({"processed": True, "credits_added": credits_to_add})
        return {"status": "credits_added", "credits": credits_to_add}

    # other events can be ignored or logged
    log_doc.update({"processed": False})
    return {"status": "ignored_event"}

@app.get("/job-status/{email}/{job_id}")
def job_status(email: str, job_id: str):
    job_ref = db.collection("users").document(email).collection("jobs").document(job_id)
    doc = job_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data = doc.to_dict()
    return {"job": data}

@app.get("/health")
def health():
    return {"status": "ok"}

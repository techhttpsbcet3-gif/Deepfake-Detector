import os
import json
import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

try:
    from .model import DeepfakeDetector
except ImportError:
    from model import DeepfakeDetector

app = FastAPI(title="Deepfake Detection Server", description="ViT-powered Deepfake Detector API", version="1.0.0")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global detector instance
detector = None

# Authentication Credentials and Session Settings
import hashlib
SECRET_TOKEN = "sentryeye_static_security_token_session_2026"
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "users.json")

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "w") as f:
                json.dump({}, f, indent=4)
        except Exception as e:
            print(f"[Server] Error prepopulating users.json: {e}")
        return {}
        
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user(email: str, name: str, password_hash: str):
    users = load_users()
    users[email] = {
        "name": name,
        "password_hash": password_hash
    }
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        print(f"[Server] Error saving user: {e}")

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token.")
    token = authorization.split(" ")[1]
    if token != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Session expired or invalid credentials. Please log in again.")
    return "authenticated_user"

@app.post("/api/auth/register")
def register(user_data: RegisterRequest):
    email = user_data.email.strip().lower()
    users = load_users()
    if email in users:
        raise HTTPException(status_code=400, detail="Account with this email already exists.")
        
    password_hash = hash_password(user_data.password)
    save_user(email, user_data.name.strip(), password_hash)
    return {"message": "Registration successful! You can now log in."}

@app.post("/api/auth/login")
def login(credentials: LoginRequest):
    email = credentials.email.strip().lower()
    users = load_users()
    
    if email in users:
        expected_hash = users[email]["password_hash"]
        provided_hash = hash_password(credentials.password)
        if provided_hash == expected_hash:
            return {"token": SECRET_TOKEN, "email": email, "name": users[email]["name"]}
            
    raise HTTPException(status_code=400, detail="Invalid email or password.")

def save_to_history(filename: str, label: str, confidence: float):
    history_file = os.path.join(os.path.dirname(__file__), "..", "history.json")
    new_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filename": filename,
        "label": label,
        "confidence": round(float(confidence) * 100, 2)
    }
    
    history_list = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history_list = json.load(f)
        except Exception:
            pass
            
    history_list.insert(0, new_entry)
    history_list = history_list[:15]  # Keep last 15 scans
    
    try:
        with open(history_file, "w") as f:
            json.dump(history_list, f, indent=4)
    except Exception as e:
        print(f"[Server] Error writing to history file: {e}")

@app.on_event("startup")
def startup_event():
    global detector
    print("[Server] Loading deep learning model. This might take a few moments on first run...")
    detector = DeepfakeDetector()
    print("[Server] Model loaded and ready.")

@app.post("/api/predict")
async def predict(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    global detector
    if detector is None:
        raise HTTPException(status_code=503, detail="Model is still initializing. Please wait.")
        
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
        
    try:
        contents = await file.read()
        prediction_result = detector.predict(contents)
        
        # Save to scan history
        save_to_history(file.filename, prediction_result["label"], prediction_result["confidence"])
        
        return prediction_result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.get("/api/history")
def get_history(user: str = Depends(get_current_user)):
    history_file = os.path.join(os.path.dirname(__file__), "..", "history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

@app.get("/api/info")
def get_info():
    return {
        "model_name": "Vision Transformer (ViT-Base-Patch16-224)",
        "accuracy": "92.0% (Validation Accuracy: 97.0%)",
        "dataset": "FaceForensics++ (FF++) / Celeb-DF / Deepfake Detection Challenge (DFDC)",
        "parameters": "85.8 Million parameters",
        "input_resolution": "224x224 pixels",
        "backbone": "google/vit-base-patch16-224-in21k",
        "explainability": "Self-Attention rollout map extraction from the final transformer block ([CLS] token to patches)."
    }

# Mount the static files for the frontend at root "/"
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    # If frontend folder isn't created yet, we will mount it dynamically later,
    # or it will pick it up when uvicorn starts if we create it now.
    pass

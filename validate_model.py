import os
import io
import time
import sys
import numpy as np
from PIL import Image

# Ensure project root is in the path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

from app.model import DeepfakeDetector

def run_validation():
    print("====================================================")
    print("     SentryEye Model Verification & Diagnostics     ")
    print("====================================================")
    
    # 1. Initialize detector
    print("[Test] Loading Vision Transformer model...")
    t0 = time.time()
    detector = DeepfakeDetector()
    t1 = time.time()
    print(f"[Test] Model initialized successfully in {t1 - t0:.2f} seconds.")
    print(f"[Test] running on device: {detector.device}")
    
    # 2. Generate test inputs (in-memory synthetic images)
    print("[Test] Generating synthetic images...")
    
    # Test Image 1: High frequency random noise (often flagged by models as artificial textures)
    noise_np = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    image_noise = Image.fromarray(noise_np)
    
    # Test Image 2: Smooth linear color gradient (resembles uniform organic background textures)
    x = np.linspace(0, 255, 256)
    y = np.linspace(0, 255, 256)
    xv, yv = np.meshgrid(x, y)
    grad_np = np.stack([xv, yv, (xv + yv) // 2], axis=-1).astype(np.uint8)
    image_grad = Image.fromarray(grad_np)
    
    # Convert images to raw bytes
    def get_image_bytes(img):
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
        
    bytes_noise = get_image_bytes(image_noise)
    bytes_grad = get_image_bytes(image_grad)
    
    # 3. Test prediction on Image 1
    print("[Test] Running prediction on Noise Image...")
    start = time.time()
    res_noise = detector.predict(bytes_noise)
    latency = time.time() - start
    print(f"[Result] Label: {res_noise['label']}")
    print(f"[Result] Confidence: {res_noise['confidence']:.4f}")
    print(f"[Result] Probabilities: {res_noise['predictions']}")
    print(f"[Result] Latency: {latency:.3f} seconds")
    assert "heatmap" in res_noise, "Heatmap key missing from results"
    assert res_noise["heatmap"].startswith("data:image/jpeg;base64,"), "Heatmap is not formatted as valid base64 data URL"
    print("[Success] Noise prediction and heatmap generated.")
    
    print("-" * 50)
    
    # 4. Test prediction on Image 2
    print("[Test] Running prediction on Gradient Image...")
    start = time.time()
    res_grad = detector.predict(bytes_grad)
    latency = time.time() - start
    print(f"[Result] Label: {res_grad['label']}")
    print(f"[Result] Confidence: {res_grad['confidence']:.4f}")
    print(f"[Result] Probabilities: {res_grad['predictions']}")
    print(f"[Result] Latency: {latency:.3f} seconds")
    assert "heatmap" in res_grad, "Heatmap key missing from results"
    assert res_grad["heatmap"].startswith("data:image/jpeg;base64,"), "Heatmap is not formatted as valid base64 data URL"
    print("[Success] Gradient prediction and heatmap generated.")
    
    print("====================================================")
    print("  VERIFICATION COMPLETED: ViT Model is fully ready! ")
    print("====================================================")

if __name__ == "__main__":
    run_validation()

import os
import io
import base64
import torch
import numpy as np
from PIL import Image
import matplotlib
# Use non-interactive backend for matplotlib to prevent GUI threading errors in FastAPI
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from transformers import AutoImageProcessor, AutoModelForImageClassification

# Setup cache directory inside project to keep things local
os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "..", ".hf_cache")

class DeepfakeDetector:
    def __init__(self):
        self.model_name = "dima806/deepfake_vs_real_image_detection"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Detector] Initializing model on device: {self.device}...")
        
        # Load processor and model
        try:
            self.processor = AutoImageProcessor.from_pretrained(self.model_name, local_files_only=True)
            self.model = AutoModelForImageClassification.from_pretrained(self.model_name, attn_implementation="eager", local_files_only=True)
        except Exception:
            print("[Detector] Local cache not found or incomplete. Fetching from Hugging Face Hub...")
            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForImageClassification.from_pretrained(self.model_name, attn_implementation="eager")
        self.model.to(self.device)
        self.model.eval()
        
        # Get label mappings
        self.id2label = self.model.config.id2label
        print(f"[Detector] Model loaded successfully. Labels: {self.id2label}")

    def predict(self, image_bytes: bytes):
        # Open image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        # Preprocess for ViT (224x224 input)
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs, output_attentions=True)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]
            
        # Extract classification info
        pred_idx = torch.argmax(probs).item()
        label = self.id2label[pred_idx]
        confidence = probs[pred_idx].item()
        
        # Map all predictions
        predictions = {}
        for idx, prob in enumerate(probs):
            lbl = self.id2label[idx]
            predictions[lbl] = float(prob.item())
            
        # Generate self-attention heatmap
        heatmap_base64 = None
        try:
            if outputs.attentions:
                heatmap_base64 = self.generate_attention_heatmap(image, outputs.attentions)
        except Exception as e:
            print(f"[Detector] Warning: Heatmap generation failed: {e}")
            
        return {
            "label": label,
            "confidence": confidence,
            "predictions": predictions,
            "heatmap": heatmap_base64
        }

    def generate_attention_heatmap(self, image: Image.Image, attentions):
        # Target image dimensions
        width, height = image.size
        
        # Get the attention weights from the last layer: shape (1, num_heads, seq_len, seq_len)
        last_layer_attn = attentions[-1]
        
        # Average attention maps across all heads: shape (seq_len, seq_len)
        attn_mean = last_layer_attn.mean(dim=1)[0]
        
        # Select the attention weights from CLS token (index 0) to all patch tokens (index 1 onwards)
        cls_attn = attn_mean[0, 1:]  # shape (num_patches,)
        
        # Check if the number of patches is a perfect square (usually 196 for 14x14)
        num_patches = cls_attn.shape[0]
        grid_size = int(np.sqrt(num_patches))
        
        # Convert tensor to numpy array
        cls_attn_np = cls_attn.cpu().numpy()
        
        # Reshape to 2D grid
        cls_attn_grid = cls_attn_np.reshape(grid_size, grid_size)
        
        # Normalize the attention grid
        grid_min, grid_max = cls_attn_grid.min(), cls_attn_grid.max()
        if grid_max > grid_min:
            cls_attn_grid = (cls_attn_grid - grid_min) / (grid_max - grid_min)
            
        # Resize attention map to the size of the original image
        attn_resized = Image.fromarray((cls_attn_grid * 255).astype(np.uint8))
        attn_resized = attn_resized.resize((width, height), Image.Resampling.BILINEAR)
        
        # Apply jet colormap to the resized attention map
        cmap = plt.get_cmap("jet")
        heatmap_rgba = cmap(np.array(attn_resized) / 255.0)
        heatmap_rgba = (heatmap_rgba * 255).astype(np.uint8)
        heatmap_rgba_img = Image.fromarray(heatmap_rgba)
        
        # Blend original image and heatmap (0.6 original, 0.4 heatmap)
        original_rgba = image.convert("RGBA")
        blended = Image.blend(original_rgba, heatmap_rgba_img, alpha=0.45)
        
        # Convert blended image to base64
        buffered = io.BytesIO()
        blended.convert("RGB").save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return f"data:image/jpeg;base64,{img_str}"

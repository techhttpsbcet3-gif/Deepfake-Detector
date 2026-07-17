import os
import io
import base64
import torch
import numpy as np
from PIL import Image
import matplotlib

# Use non-interactive backend for matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification,
)

# Hugging Face cache directory
os.environ["HF_HOME"] = os.path.join(
    os.path.dirname(__file__),
    "..",
    ".hf_cache"
)


class DeepfakeDetector:
    def __init__(self):
        self.model_name = "dima806/deepfake_vs_real_image_detection"
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(f"[Detector] Initializing model on device: {self.device}...")
        print("[Detector] Downloading/loading model from Hugging Face...")

        # Load processor
        self.processor = AutoImageProcessor.from_pretrained(
            self.model_name
        )

        # Load model
        self.model = AutoModelForImageClassification.from_pretrained(
            self.model_name,
            attn_implementation="eager"
        )

        self.model.to(self.device)
        self.model.eval()

        self.id2label = self.model.config.id2label

        print("[Detector] Model loaded successfully.")
        print(f"[Detector] Labels: {self.id2label}")

    def predict(self, image_bytes: bytes):
        image = Image.open(io.BytesIO(image_bytes))

        if image.mode != "RGB":
            image = image.convert("RGB")

        inputs = self.processor(
            images=image,
            return_tensors="pt"
        )

        inputs = {
            k: v.to(self.device)
            for k, v in inputs.items()
        }

        with torch.no_grad():
            outputs = self.model(
                **inputs,
                output_attentions=True
            )

            logits = outputs.logits
            probs = torch.nn.functional.softmax(
                logits,
                dim=-1
            )[0]

        pred_idx = torch.argmax(probs).item()
        label = self.id2label[pred_idx]
        confidence = probs[pred_idx].item()

        predictions = {}

        for idx, prob in enumerate(probs):
            predictions[self.id2label[idx]] = float(prob.item())

        heatmap = None

        try:
            if outputs.attentions:
                heatmap = self.generate_attention_heatmap(
                    image,
                    outputs.attentions
                )
        except Exception as e:
            print(f"[Detector] Heatmap generation failed: {e}")

        return {
            "label": label,
            "confidence": confidence,
            "predictions": predictions,
            "heatmap": heatmap,
        }

    def generate_attention_heatmap(self, image, attentions):
        width, height = image.size

        last_layer = attentions[-1]
        attention = last_layer.mean(dim=1)[0]
        cls_attention = attention[0, 1:]

        patches = cls_attention.shape[0]
        grid = int(np.sqrt(patches))

        attention = cls_attention.cpu().numpy().reshape(grid, grid)

        if attention.max() > attention.min():
            attention = (
                attention - attention.min()
            ) / (attention.max() - attention.min())

        attention = Image.fromarray(
            (attention * 255).astype(np.uint8)
        )

        attention = attention.resize(
            (width, height),
            Image.Resampling.BILINEAR
        )

        cmap = plt.get_cmap("jet")

        heatmap = cmap(np.array(attention) / 255.0)
        heatmap = (heatmap * 255).astype(np.uint8)

        heatmap = Image.fromarray(heatmap)

        blended = Image.blend(
            image.convert("RGBA"),
            heatmap,
            alpha=0.45
        )

        buffer = io.BytesIO()
        blended.convert("RGB").save(buffer, format="JPEG")

        return (
            "data:image/jpeg;base64,"
            + base64.b64encode(buffer.getvalue()).decode()
        )
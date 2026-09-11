import os
import gc
import traceback
import numpy as np
import cv2
from PIL import Image


class DiabCareModel:
    def __init__(self):
        self.session = None
        self.demo_mode = True
        self.model_path = os.path.join(os.path.dirname(__file__), 'best.onnx')
        self.classes = ['Normal', 'Ulcer']
        self._check_model()

    def _check_model(self):
        if not os.path.exists(self.model_path):
            self.demo_mode = True
            print("No best.onnx - running DEMO mode.")
            return
        self.demo_mode = False
        print(f"Found trained model: {self.model_path}")

    def _load_session(self):
        if self.session is not None:
            return self.session
        try:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 2
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(self.model_path, opts)
            return self.session
        except Exception as e:
            print(f"ONNX load error: {e}")
            self.demo_mode = True
            return None

    def _unload(self):
        if self.session is not None:
            del self.session
            self.session = None
            gc.collect()

    def _demo_result(self):
        return 'Normal', 0.5, None

    def preprocess(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        h, w = img.shape[:2]
        max_side = 1024
        if max(h, w) > max_side:
            scale = max_side / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_AREA)
            cv2.imwrite(image_path, img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img)
        return img_pil, img

    def generate_heatmap(self, img_array, prediction_confidence):
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        heatmap = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        if prediction_confidence > 0.5:
            overlay = cv2.addWeighted(img_array, 0.6, heatmap, 0.4, 0)
        else:
            overlay = cv2.addWeighted(img_array, 0.8, heatmap, 0.2, 0)
        return overlay

    def predict(self, image_path):
        img_pil, img_array = self.preprocess(image_path)
        demo_note = None

        session = self._load_session() if not self.demo_mode else None

        if session is not None:
            try:
                # Resize to 224x224 for model input
                img_resized = img_pil.resize((320, 320), Image.BILINEAR)
                img_np = np.array(img_resized, dtype=np.float32) / 255.0
                img_np = (img_np - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array([0.229, 0.224, 0.225], dtype=np.float32)
                img_np = img_np.transpose(2, 0, 1)  # HWC -> CHW
                img_np = np.expand_dims(img_np, 0)   # add batch dim

                input_name = session.get_inputs()[0].name
                outputs = session.run(None, {input_name: img_np})
                probs = outputs[0][0]

                predicted_class = int(np.argmax(probs))
                confidence = float(probs[predicted_class])
                prediction = self.classes[predicted_class]
            except Exception:
                traceback.print_exc()
                prediction, confidence, demo_note = self._demo_result()
            finally:
                self._unload()
        else:
            prediction, confidence, demo_note = self._demo_result()

        risk_level = self._calculate_risk(confidence, prediction)

        heatmap = self.generate_heatmap(img_array, confidence)
        heatmap_filename = f"heatmap_{os.path.basename(image_path)}"
        heatmap_path = os.path.join(os.path.dirname(image_path), heatmap_filename)
        cv2.imwrite(heatmap_path, cv2.cvtColor(heatmap, cv2.COLOR_RGB2BGR))

        recommendations = self._get_recommendations(risk_level, prediction)
        if demo_note:
            recommendations = [demo_note] + recommendations

        return {
            'prediction': prediction,
            'confidence': round(confidence * 100, 2),
            'risk_level': risk_level,
            'risk_score': self._risk_score(confidence, prediction),
            'recommendations': recommendations,
            'heatmap_path': heatmap_path,
            'heatmap_url': f'/api/image/{heatmap_filename}',
            'demo_mode': self.demo_mode or demo_note is not None
        }

    def _calculate_risk(self, confidence, prediction):
        if prediction == 'Ulcer':
            return 'MEDIUM'
        else:
            if confidence > 0.7:
                return 'LOW'
            else:
                return 'UNCERTAIN'

    def _risk_score(self, confidence, prediction):
        if prediction == 'Ulcer':
            return round(confidence * 100, 1)
        else:
            return round((1 - confidence) * 100, 1)

    def _get_recommendations(self, risk_level, prediction):
        recommendations = {
            'HIGH': [
                'Urgent: Seek professional medical evaluation immediately',
                'Keep the affected area clean and dry',
                'Avoid putting pressure on the foot',
                'Document the wound with daily photos'
            ],
            'MEDIUM': [
                'Schedule a medical appointment for professional evaluation',
                'Monitor the area daily for changes',
                'Keep feet clean and properly moisturized',
                'Check blood glucose levels regularly'
            ],
            'LOW': [
                'Continue regular foot inspections',
                'Maintain proper foot hygiene',
                'Wear appropriate footwear',
                'Schedule routine diabetic foot screening'
            ],
            'UNCERTAIN': [
                'Retake the image with better lighting',
                'Ensure the foot is clean and dry',
                'Consult a healthcare professional for clarification',
                'Try a different angle for the photo'
            ]
        }
        return recommendations.get(risk_level, recommendations['UNCERTAIN'])

from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np
import os
import sys
import sklearn
import xgboost as xgb
import lightgbm as lgb

app = Flask(__name__, template_folder="templates")

# --------------------- Setup Info --------------------- #
print(f"🐍 Python version: {sys.version}")
print(f"📦 numpy version: {np.__version__}")
print(f"📦 pandas version: {pd.__version__}")
print(f"📦 scikit-learn version: {sklearn.__version__}")
print(f"📦 xgboost version: {xgb.__version__}")
print(f"📦 lightgbm version: {lgb.__version__}")

# --------------------- Model Load --------------------- #
try:
    model_path = os.path.join("models", "Anemia_classifier_model.pkl")
    if not os.path.exists(model_path):
        raise FileNotFoundError("Model file not found at expected path.")

    package = joblib.load(model_path)
    model = package["model"]
    metadata = package["metadata"]

    # ✅ Backward compatibility
    metadata.setdefault(
        "reference_ranges",
        {
            "HGB": (12.0, 16.0),
            "RBC": (4.0, 5.5),
            "PCV": (37.0, 47.0),
            "MCV": (80.0, 100.0),
            "MCHC": (32.0, 36.0),
            "RDW": (11.5, 14.5),
        },
    )

    reference_ranges = metadata["reference_ranges"]

    print("✅ Model loaded successfully!")
    print(f"✅ Features: {metadata['features']}")
    print(f"✅ Classes: {metadata['class_names']}")

except Exception as e:
    print(f"❌ Model load failed: {e}")
    model, metadata = None, {"features": [], "class_names": [], "reference_ranges": {}}

# --------------------- Routes --------------------- #


@app.route("/")
def home():
    """Main page"""
    return render_template(
        "index.html",
        parameters=metadata["features"],
        reference_ranges=metadata["reference_ranges"],
        model_loaded=(model is not None),
    )


@app.route("/predict", methods=["POST"])
def predict():
    """Handle prediction"""
    try:
        if model is None:
            return jsonify({"error": "Model not loaded"}), 500

        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing input JSON"}), 400

        missing = [f for f in metadata["features"] if f not in data]
        if missing:
            return jsonify({"error": f"Missing parameters: {missing}"}), 400

        input_df = pd.DataFrame([data])[metadata["features"]]
        input_df = input_df.apply(pd.to_numeric, errors="coerce")
        if input_df.isnull().any().any():
            return jsonify({"error": "Invalid numeric values detected"}), 400

        prediction_idx = model.predict(input_df)[0]
        prediction = metadata["class_names"][prediction_idx]

        response = {
            "prediction": prediction,
            "model_version": metadata.get("version", "1.0"),
            "features_used": metadata["features"],
        }

        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(input_df)[0]
            response["confidence_scores"] = {
                cls: float(proba[i]) for i, cls in enumerate(metadata["class_names"])
            }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route("/health")
def health_check():
    return jsonify(
        {
            "status": "healthy" if model else "degraded",
            "model_loaded": bool(model),
            "features": metadata.get("features", []),
            "classes": metadata.get("class_names", []),
        }
    )


# --------------------- Run Server --------------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

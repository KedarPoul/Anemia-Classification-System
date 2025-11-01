from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np
import os

app = Flask(__name__, template_folder="templates")

# FIXED: Model loading with error handling for production
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "models", "Anemia_classifier_model.pkl")

    # Check if model file exists
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at: {model_path}")

    model_package = joblib.load(model_path)
    model = model_package["model"]
    metadata = model_package["metadata"]
    reference_ranges = metadata["reference_ranges"]
    required_params = metadata["features"]

    print(f"✅ Model loaded successfully from: {model_path}")
    print(f"✅ Features: {required_params}")
    print(f"✅ Class names: {metadata['class_names']}")

except Exception as e:
    print(f"❌ Failed to load model: {str(e)}")
    # Create a simple model for testing if real model fails
    print("⚠️  Using fallback mode - model predictions will not work")
    model = None
    metadata = {
        "features": ["Age", "Sex", "RBC", "PCV", "MCV", "MCHC", "RDW", "HGB"],
        "class_names": [
            "No_Anemia",
            "ACD_Moderate",
            "ACD_Severe",
            "Moderate_iron_deficiency_anemia",
        ],
        "reference_ranges": {
            "HGB": [12.0, 16.0],
            "RBC": [4.0, 5.5],
            "PCV": [37.0, 47.0],
            "MCV": [80.0, 100.0],
            "MCHC": [32.0, 36.0],
            "RDW": [11.5, 14.5],
        },
    }
    reference_ranges = metadata["reference_ranges"]
    required_params = metadata["features"]


@app.route("/")
def home():
    """Render main form page"""
    return render_template(
        "index.html",
        parameters=required_params,
        reference_ranges=reference_ranges,
        model_loaded=model is not None,
    )


@app.route("/predict", methods=["POST"])
def predict():
    """Handle prediction requests"""
    try:
        # Check if model is loaded
        if model is None:
            return jsonify(
                {
                    "error": "Model not loaded",
                    "message": "The ML model failed to load. Please check the server logs.",
                }
            ), 500

        # Validate request format
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.json

        # Check for required parameters
        missing = [param for param in metadata["features"] if param not in data]
        if missing:
            return jsonify({"error": f"Missing parameters: {missing}"}), 400

        # Create input DataFrame
        try:
            input_df = pd.DataFrame([data])[metadata["features"]]
        except Exception as e:
            return jsonify({"error": f"Data conversion error: {str(e)}"}), 400

        # Convert critical columns to float
        float_columns = ["PCV", "MCV", "MCHC", "RDW", "HGB", "RBC", "Age"]
        for col in float_columns:
            if col in input_df.columns:
                input_df[col] = pd.to_numeric(input_df[col], errors="coerce").astype(
                    "float64"
                )

        # Handle potential conversion errors
        if input_df.isnull().any().any():
            return jsonify({"error": "Invalid numeric values detected"}), 400

        # Validate against clinical reference ranges
        validation_errors = validate_parameters(input_df)
        alerts = {}
        if validation_errors:
            alerts = {
                "warning": "Abnormal parameters detected",
                "abnormal_values": validation_errors,
            }

        # Ensure correct feature order and presence
        try:
            input_processed = input_df[metadata["features"]]
            missing = [
                f for f in metadata["features"] if f not in input_processed.columns
            ]
            if missing:
                return jsonify({"error": f"Missing parameters: {missing}"}), 400
        except Exception as e:
            return jsonify({"error": f"Feature validation failed: {str(e)}"}), 400

        # Make prediction
        try:
            prediction_idx = model.predict(input_processed)[0]
            prediction = metadata["class_names"][prediction_idx]
        except Exception as e:
            app.logger.error(f"Prediction error details: {str(e)}")
            app.logger.error(f"Input features: {input_processed.columns.tolist()}")
            app.logger.error(f"Expected features: {metadata['features']}")
            return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

        # Build response
        response = {
            "prediction": prediction,
            "model_metadata": {
                "version": metadata.get("version", "1.0"),
                "features_used": metadata["features"],
                "reference_ranges": metadata["reference_ranges"],
            },
        }

        # Add probabilities if available
        if hasattr(model, "predict_proba"):
            try:
                proba = model.predict_proba(input_processed)[0]
                proba = np.clip(proba, 1e-12, 1 - 1e-12)
                response["confidence_scores"] = {
                    cls: float(proba[idx])
                    for idx, cls in enumerate(metadata["class_names"])
                }
            except Exception as e:
                app.logger.error(f"Probability error: {str(e)}")
                response["warning"] = "Confidence estimates unavailable"

        # Include any validation alerts
        if alerts:
            response.update(alerts)

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"Server error: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


def validate_parameters(df):
    """Validate parameters against clinical reference ranges"""
    alerts = {}
    for param, (low, high) in reference_ranges.items():
        if param in df.columns:
            try:
                value = pd.to_numeric(df[param].iloc[0], errors="coerce")
                if not (low <= value <= high):
                    alerts[param] = {
                        "value": float(value),
                        "normal_range": [float(low), float(high)],
                        "unit": metadata.get("units", {}).get(param, ""),
                    }
            except Exception:
                alerts[param] = "Invalid numeric value"
    return alerts


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy" if model is not None else "degraded",
            "model_loaded": model is not None,
            "features": metadata["features"],
            "class_names": metadata["class_names"],
        }
    )


@app.errorhandler(404)
def not_found(error):
    return jsonify(
        {
            "error": "Endpoint not found. Available endpoints: GET /, POST /predict, GET /health"
        }
    ), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


# Production configuration
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    print("🚀 Starting Anemia Classification Server...")
    print(f"📍 Port: {port}")
    print(f"🐛 Debug: {debug_mode}")
    print(f"📊 Model status: {'✅ Loaded' if model is not None else '❌ Failed'}")

    app.run(host="0.0.0.0", port=port, debug=debug_mode)

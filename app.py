from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np
import os  # ADD THIS

app = Flask(__name__, template_folder="templates")

# FIXED: Model loading with relative path
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "models", "Anemia_classifier_model.pkl")

    model_package = joblib.load(model_path)
    model = model_package["model"]
    metadata = model_package["metadata"]
    reference_ranges = metadata["reference_ranges"]
    required_params = metadata["features"]
    print(f"✅ Model loaded successfully from: {model_path}")

except Exception as e:
    print(f"❌ Failed to load model: {str(e)}")
    # In production, we might want to exit if model can't load
    raise e


@app.route("/")
def home():
    """Render main form page"""
    return render_template(
        "index.html", parameters=required_params, reference_ranges=reference_ranges
    )


@app.route("/predict", methods=["POST"])
def predict():
    """Handle prediction requests"""
    try:
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
        float_columns = ["PCV", "MCV", "MCHC", "RDW", "HGB", "RBC"]
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


def add_medical_features(df):
    """Create clinical feature ratios"""
    ratios = {"HgB/RBC": ("HGB", "RBC"), "RDW/MCV": ("RDW", "MCV")}
    for new_feature, (num, den) in ratios.items():
        if num in df.columns and den in df.columns:
            df[new_feature] = df[num] / df[den]
    return df


def validate_parameters(df):
    """With type safety"""
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
            except:  # noqa: E722
                alerts[param] = "Invalid numeric value"
    return alerts


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found. Use POST /predict"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed. Use POST for /predict"}), 405


# Production configuration
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    print("🚀 Starting Anemia Classification Server...")
    print(f"📍 Port: {port}")
    print(f"🐛 Debug: {debug_mode}")

    app.run(host="0.0.0.0", port=port, debug=debug_mode)

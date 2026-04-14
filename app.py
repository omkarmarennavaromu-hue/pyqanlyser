import os
from flask import Flask
from api import register_routes

app = Flask(__name__, template_folder="templates")

# -----------------------------
# CONFIGURATION (PRODUCTION SAFE)
# -----------------------------

# Secret key (must be set in environment for production)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

app.config["UPLOAD_FOLDER"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads"
)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB limit
app.config["ALLOWED_EXTENSIONS"] = {"pdf"}

# -----------------------------
# ENSURE UPLOAD DIRECTORY EXISTS
# -----------------------------
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# -----------------------------
# ROUTES REGISTRATION
# -----------------------------
register_routes(app)

# -----------------------------
# HELPER FUNCTION
# -----------------------------
def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )

# -----------------------------
# LOCAL DEVELOPMENT ONLY
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)

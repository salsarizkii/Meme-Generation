from flask import Blueprint, jsonify
import json
import os

# Blueprint untuk daftar meme templates
memes_bp = Blueprint("memes", __name__)

# Path absolut ke project root (satu level di atas folder routes)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MEMES_PATH = os.path.join(BASE_DIR, "memes.json")

# Load data meme dari file JSON
with open(MEMES_PATH, encoding="utf-8") as f:
    MEMES = json.load(f)


@memes_bp.route("/get_memes", methods=["GET"])
def get_memes():
    """
    Response mirip Imgflip:
    {
      "success": true,
      "data": {
        "memes": [ ... ]
      }
    }
    """
    return jsonify({
        "success": True,
        "data": {
            "memes": MEMES
        }
    })


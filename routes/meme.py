from flask import Flask
from routes.memes import memes_bp
from routes.caption import caption_bp

app = Flask(__name__)

# daftar route
app.register_blueprint(memes_bp)
app.register_blueprint(caption_bp)

if __name__ == "__main__":
    app.run(debug=True)


from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import redis
from .config.settings import config

db  = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    app.redis_client = redis.from_url(app.config['REDIS_URL'])

    # Enregistrer les routes (Blueprints)
    from .routes.auth import auth_bp
    from .routes.chat import chat_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')

    @app.route('/')
    def home():
        return {'status': 'ok', 'message': 'Backend IA Médical ✓'}

    return app
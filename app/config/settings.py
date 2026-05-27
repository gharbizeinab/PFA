import os
from dotenv import load_dotenv

load_dotenv()  # charge automatiquement le fichier .env

class Config:
    SECRET_KEY                  = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI     = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY              = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES    = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    OLLAMA_BASE_URL             = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_CHAT_MODEL           = os.getenv('OLLAMA_CHAT_MODEL', 'llama3.2:3b')
    OLLAMA_SQL_MODEL            = os.getenv('OLLAMA_SQL_MODEL', 'qwen2.5-coder:7b')
    REDIS_URL                   = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig
}
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask_socketio import SocketIO
from config import Config

# Initialize SocketIO with more permissive cors settings
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Initialize SocketIO with app
    socketio.init_app(app, cors_allowed_origins="*", ping_timeout=60)
    
    # Register blueprints
    from app.controllers.upload_controller import upload_bp
    app.register_blueprint(upload_bp)
    
    return app
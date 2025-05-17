#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    RESULT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    ALLOWED_EXTENSIONS = {'csv'}
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max upload (changed from 50MB)
    
    @staticmethod
    def init_app(app):
        # Create necessary directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESULT_FOLDER, exist_ok=True)
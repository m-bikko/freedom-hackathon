#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Use socketio.run instead of app.run for proper WebSocket handling
    socketio.run(app, host='0.0.0.0', port=5006, debug=False, allow_unsafe_werkzeug=True)
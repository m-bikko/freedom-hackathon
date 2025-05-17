#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app.models.recommendation_model import RecommendationModel
from app import socketio
import threading

upload_bp = Blueprint('upload', __name__)

# Dictionary to store processing status for each session
processing_status = {}

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def process_recommendation(train_test_path, events_description_path, output_path, session_id):
    """Process the recommendation model in a separate thread"""
    try:
        # Update status
        processing_status[session_id] = {
            'status': 'processing',
            'message': 'Starting recommendation process...',
            'percentage': 0
        }
        
        # Create and run the recommendation model
        model = RecommendationModel(
            train_test_path=train_test_path,
            events_description_path=events_description_path,
            output_path=output_path,
            socketio=socketio
        )
        result_path = model.run()
        
        # Update status
        processing_status[session_id] = {
            'status': 'completed',
            'message': 'Processing completed successfully!',
            'percentage': 100,
            'result_file': os.path.basename(result_path)
        }
        
        # Emit completion event
        socketio.emit('completion', {
            'success': True,
            'message': 'Processing completed successfully!',
            'result_file': os.path.basename(result_path),
            'session_id': session_id
        })
    except Exception as e:
        # Update status
        processing_status[session_id] = {
            'status': 'error',
            'message': f'Error during processing: {str(e)}',
            'percentage': 100
        }
        
        # Emit error event
        socketio.emit('completion', {
            'success': False,
            'message': f'Error during processing: {str(e)}',
            'session_id': session_id
        })

@upload_bp.route('/')
def index():
    """Render the file upload form"""
    return render_template('index.html')

@upload_bp.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and start processing"""
    # Check if both required files were uploaded
    if 'train_test' not in request.files or 'events_description' not in request.files:
        flash('Both files are required')
        return redirect(request.url)
    
    train_test_file = request.files['train_test']
    events_description_file = request.files['events_description']
    
    # Check if filenames are empty
    if train_test_file.filename == '' or events_description_file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    if (train_test_file and allowed_file(train_test_file.filename) and 
        events_description_file and allowed_file(events_description_file.filename)):
        
        # Save both files
        train_test_filename = secure_filename(train_test_file.filename)
        events_description_filename = secure_filename(events_description_file.filename)
        
        train_test_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                      f"{session_id}_{train_test_filename}")
        events_description_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                             f"{session_id}_{events_description_filename}")
        
        train_test_file.save(train_test_path)
        events_description_file.save(events_description_path)
        
        # Set output path
        output_filename = f"{session_id}_result.csv"
        output_path = os.path.join(current_app.config['RESULT_FOLDER'], output_filename)
        
        # Initialize status
        processing_status[session_id] = {
            'status': 'starting',
            'message': 'Starting the process...',
            'percentage': 0
        }
        
        # Start processing in a separate thread
        threading.Thread(
            target=process_recommendation,
            args=(train_test_path, events_description_path, output_path, session_id)
        ).start()
        
        # Redirect to processing page
        return redirect(url_for('upload.processing', session_id=session_id))
    
    flash('Invalid file type. Only CSV files are allowed.')
    return redirect(request.url)

@upload_bp.route('/processing/<session_id>')
def processing(session_id):
    """Render the processing page with progress monitoring"""
    return render_template('processing.html', session_id=session_id)

@upload_bp.route('/api/status/<session_id>')
def check_status(session_id):
    """API endpoint to check processing status without WebSocket"""
    if session_id in processing_status:
        return jsonify(processing_status[session_id])
    return jsonify({'status': 'unknown', 'message': 'Session not found'})

@upload_bp.route('/result/<session_id>')
def result(session_id):
    """Render the result page with download link"""
    result_filename = f"{session_id}_result.csv"
    return render_template('result.html', 
                          result_file=result_filename,
                          session_id=session_id)

@upload_bp.route('/download/<filename>')
def download_file(filename):
    """Handle file download request"""
    return send_from_directory(current_app.config['RESULT_FOLDER'], filename, as_attachment=True)
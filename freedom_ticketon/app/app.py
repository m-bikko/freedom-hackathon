import os
import time
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from werkzeug.utils import secure_filename

from app.controllers import file_controller, recommendation_controller
from app.models import model

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'uploads')
app.config['MODEL_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'models')
app.secret_key = 'freedom_ticketon_secret_key'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MODEL_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'train_test' not in request.files or 'events_description' not in request.files:
        # Missing files, redirect back to index
        return redirect(url_for('index'))
    
    train_file = request.files['train_test']
    events_file = request.files['events_description']
    
    if train_file.filename == '' or events_file.filename == '':
        # No files selected, redirect back to index
        return redirect(url_for('index'))
    
    # Save the files
    train_path = file_controller.upload_file(train_file, 'train_test')
    events_path = file_controller.upload_file(events_file, 'events_description')
    
    if not train_path or not events_path:
        # File upload failed, redirect back to index
        return redirect(url_for('index'))
    
    # Start processing in a separate thread
    recommendation_controller.start_processing(train_path, events_path)
    
    # Store start time for tracking processing duration
    session['process_start_time'] = time.time()
    
    # Redirect to processing page
    return redirect(url_for('processing'))

@app.route('/processing')
def processing():
    # Check if processing has started
    if not session.get('processing_started', False):
        return redirect(url_for('index'))
    
    return render_template('processing.html')

@app.route('/progress')
def progress():
    # Get current progress and check if processing is complete
    current_progress = recommendation_controller.get_processing_progress()
    is_complete = recommendation_controller.is_processing_complete()
    
    return jsonify({
        'progress': current_progress,
        'complete': is_complete
    })

@app.route('/results')
def results():
    # Check if processing has completed
    if not recommendation_controller.is_processing_complete():
        return redirect(url_for('processing'))
    
    # Get result file path
    result_path = recommendation_controller.get_result_path()
    if not result_path or not os.path.exists(result_path):
        return redirect(url_for('index'))
    
    # Read result file for preview
    result_df = pd.read_csv(result_path)
    preview = result_df.head(10).to_dict('records')
    
    # Calculate statistics
    stats = {
        'user_count': len(result_df),
        'recommendation_count': sum(len(row.get('items_id', '').split()) for _, row in result_df.iterrows()),
        'processing_time': format_processing_time(session.get('process_start_time', 0))
    }
    
    return render_template('results.html', preview=preview, stats=stats)

@app.route('/download')
def download_results():
    # Get result file path
    result_path = session.get('result_path', None)
    if not result_path or not os.path.exists(result_path):
        return redirect(url_for('index'))
    
    # Send file for download
    return send_file(
        result_path,
        as_attachment=True,
        download_name='freedom_ticketon_recommendations.csv',
        mimetype='text/csv'
    )

def format_processing_time(start_time):
    """Format processing time into a readable string"""
    if not start_time:
        return "Unknown"
    
    elapsed = time.time() - start_time
    
    if elapsed < 60:
        return f"{elapsed:.1f} seconds"
    elif elapsed < 3600:
        minutes = elapsed / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = elapsed / 3600
        return f"{hours:.1f} hours"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
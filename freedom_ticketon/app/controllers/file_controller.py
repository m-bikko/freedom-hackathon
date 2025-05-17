import os
import pandas as pd
from flask import current_app, session
from werkzeug.utils import secure_filename

def allowed_file(filename):
    """Check if the file is allowed based on extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

def upload_file(file, file_type):
    """Save uploaded file and return file path"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Use file_type as filename to standardize
        save_filename = f"{file_type}.csv"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_path = os.path.join(upload_folder, save_filename)
        file.save(file_path)
        
        # Store the path in session
        session[f'{file_type}_path'] = file_path
        return file_path
    return None

def get_file_paths():
    """Get paths for train and events files from session"""
    train_path = session.get('train_test_path', None)
    events_path = session.get('events_description_path', None)
    return train_path, events_path

def save_recommendations(recommendations, output_path=None):
    """Save recommendations to CSV file"""
    if not output_path:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        output_path = os.path.join(upload_folder, 'result.csv')
    
    # Format recommendations for CSV
    data = []
    for user_id, items in recommendations.items():
        items_str = ' '.join(items) if items else ''
        data.append({'user_id': user_id, 'items_id': items_str})
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    session['result_path'] = output_path
    
    return output_path

def extract_users_from_test(test_path):
    """Extract users who need recommendations from test set"""
    df = pd.read_csv(test_path)
    test_users = df[df['part_dataset'] == 'test']['user_id'].unique().tolist()
    return test_users
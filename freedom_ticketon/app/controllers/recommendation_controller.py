import os
import threading
import time
from flask import current_app, session
from app.models import model
from app.controllers.file_controller import extract_users_from_test, save_recommendations

class ProcessThread(threading.Thread):
    def __init__(self, train_path, events_path):
        super(ProcessThread, self).__init__()
        self.train_path = train_path
        self.events_path = events_path
        self.result = None
        self._stop_event = threading.Event()
        
    def run(self):
        try:
            # 1. Load data
            model.load_data(self.train_path, self.events_path)
            if self._stop_event.is_set():
                return
                
            # 2. Preprocess data
            model.preprocess_data()
            if self._stop_event.is_set():
                return
                
            # 3. Build model
            model.build_model()
            if self._stop_event.is_set():
                return
                
            # 4. Generate recommendations for test users
            test_users = extract_users_from_test(self.train_path)
            recommendations = model.make_recommendations(test_users, top_n=5)
            
            # 5. Save recommendations
            output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'result.csv')
            save_recommendations(recommendations, output_path)
            
            # 6. Save model for future use
            model_path = os.path.join(current_app.config['MODEL_FOLDER'], 'recommendation_model.pkl')
            os.makedirs(current_app.config['MODEL_FOLDER'], exist_ok=True)
            model.save_model(model_path)
            
            self.result = output_path
        except Exception as e:
            print(f"Error in processing thread: {e}")
            self.result = None
            
    def stop(self):
        self._stop_event.set()

# Global variable to store the processing thread
_processing_thread = None

def start_processing(train_path, events_path):
    """Start processing data in a separate thread"""
    global _processing_thread
    
    # Stop existing thread if there is one
    if _processing_thread and _processing_thread.is_alive():
        _processing_thread.stop()
        
    # Create and start new thread
    _processing_thread = ProcessThread(train_path, events_path)
    _processing_thread.start()
    
    # Store paths in session
    session['train_test_path'] = train_path
    session['events_description_path'] = events_path
    session['processing_started'] = True
    
    return True

def get_processing_progress():
    """Get current progress of the processing"""
    if not model:
        return 0
    return model.get_progress()

def is_processing_complete():
    """Check if processing is complete"""
    global _processing_thread
    
    if not _processing_thread:
        return False
        
    return not _processing_thread.is_alive()

def get_result_path():
    """Get the path to the result file"""
    global _processing_thread
    
    if _processing_thread and not _processing_thread.is_alive():
        return _processing_thread.result
    return None
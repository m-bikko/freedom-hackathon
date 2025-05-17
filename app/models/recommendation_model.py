#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
import os
import sys
import time

class RecommendationModel:
    def __init__(self, train_test_path, events_description_path, output_path, socketio=None):
        """
        Initialize the recommendation model with input file paths
        
        Parameters:
        -----------
        train_test_path: str
            Path to the train_test.csv file
        events_description_path: str
            Path to the events_description.csv file
        output_path: str
            Path where the result CSV will be saved
        socketio: SocketIO
            Socket.IO instance for real-time progress updates
        """
        self.train_test_path = train_test_path
        self.events_description_path = events_description_path
        self.output_path = output_path
        self.socketio = socketio
        
        # Get session ID from filenames for status updates
        self.session_id = None
        if os.path.basename(train_test_path).count('_') > 0:
            self.session_id = os.path.basename(train_test_path).split('_')[0]
        
    def emit_progress(self, message, percentage=None):
        """Send progress update via Socket.IO if available"""
        try:
            # Update global status dictionary if we have a session ID
            if self.session_id:
                from app.controllers.upload_controller import processing_status
                if self.session_id in processing_status:
                    processing_status[self.session_id]['message'] = message
                    if percentage is not None:
                        processing_status[self.session_id]['percentage'] = percentage
            
            # Send via Socket.IO if available
            if self.socketio:
                data = {'message': message}
                if percentage is not None:
                    data['percentage'] = percentage
                self.socketio.emit('progress', data)
                # Small delay to ensure the message is sent
                time.sleep(0.05)
        except Exception as e:
            print(f"Error sending progress update: {e}")
    
    def run(self):
        """Execute the recommendation process"""
        try:
            self.emit_progress("Starting recommendation process...", 0)
            
            # 1. Load data
            self.emit_progress("Loading data...", 5)
            train_test = pd.read_csv(self.train_test_path)
            events_description = pd.read_csv(self.events_description_path)
            submission = pd.DataFrame(columns=['user_id', 'item_ids'])
            
            self.emit_progress("Data loaded successfully. Converting timestamps...", 10)
            
            # 2. Preprocess data
            # Convert reservation_time to datetime
            train_test['reservation_time'] = pd.to_datetime(train_test['reservation_time'])
            
            # Filter paid interactions
            paid_interactions = train_test[train_test['sale_status'] == 'PAID'].copy()
            self.emit_progress(f"Filtered to {len(paid_interactions)} PAID interactions", 15)
            
            # Identify candidate events
            april_candidates = events_description[events_description['part_dataset'] == 'submission_movies']['item_id'].unique()
            march_candidates = events_description[events_description['part_dataset'] == 'test']['item_id'].unique()
            
            self.emit_progress(f"Found {len(april_candidates)} candidate events for April", 20)
            
            # 3. Split user interactions
            history_interactions = paid_interactions[paid_interactions['part_dataset'] == 'train'].copy()
            march_interactions = paid_interactions[paid_interactions['part_dataset'] == 'test'].copy()
            full_history_interactions = paid_interactions[paid_interactions['part_dataset'].isin(['train', 'test'])].copy()
            
            # Create ground truth for March
            march_ground_truth = march_interactions.groupby('user_id')['item_id'].apply(list).to_dict()
            
            # Merge interactions with event details
            history_with_details = pd.merge(history_interactions, events_description, on='item_id', how='left')
            march_with_details = pd.merge(march_interactions, events_description, on='item_id', how='left')
            full_history_with_details = pd.merge(full_history_interactions, events_description, on='item_id', how='left')
            
            self.emit_progress("Processed interaction data", 25)
            
            # 4. Create mappings
            # User mappings
            user_city = paid_interactions[['user_id', 'city']].drop_duplicates().set_index('user_id')['city'].to_dict()
            user_gender = paid_interactions[['user_id', 'gender_main']].drop_duplicates().set_index('user_id')['gender_main'].to_dict()
            user_age = paid_interactions[['user_id', 'age']].drop_duplicates().set_index('user_id')['age'].to_dict()
            
            self.emit_progress("Created user mappings", 30)
            
            # Event mappings
            event_city, event_place = self.get_event_city_mappings(paid_interactions)
            
            event_genre = events_description[['item_id', 'film_genre']].drop_duplicates().set_index('item_id')['film_genre'].to_dict()
            event_type = events_description[['item_id', 'film_type']].drop_duplicates().set_index('item_id')['film_type'].to_dict()
            
            self.emit_progress("Created event mappings", 35)
            
            # 5. Calculate popularity
            self.emit_progress("Calculating popularity scores...", 40)
            
            # Calculate popularity scores
            march_popularity = self.calculate_popularity(history_interactions, march_candidates)
            april_popularity = self.calculate_popularity(full_history_interactions, april_candidates)
            
            # Calculate city-specific popularity
            march_city_popularity = self.calculate_city_popularity(history_interactions, march_candidates)
            april_city_popularity = self.calculate_city_popularity(full_history_interactions, april_candidates)
            
            self.emit_progress("Calculated popularity scores", 45)
            
            # 6. Extract temporal patterns
            self.emit_progress("Extracting temporal patterns...", 50)
            
            # Extract user temporal patterns
            history_frequency, history_day_prefs, history_hour_prefs = self.extract_user_temporal_patterns(history_interactions)
            full_frequency, full_day_prefs, full_hour_prefs = self.extract_user_temporal_patterns(full_history_interactions)
            
            # Extract event temporal patterns
            march_day_patterns, march_hour_patterns = self.extract_event_temporal_patterns(history_interactions, march_candidates)
            april_day_patterns, april_hour_patterns = self.extract_event_temporal_patterns(full_history_interactions, april_candidates)
            
            self.emit_progress("Extracted temporal patterns", 60)
            
            # 7. Generate April predictions
            self.emit_progress("Generating recommendations...", 65)
            
            april_predictions = {}
            submission_users = list(set(paid_interactions['user_id'].unique()))
            
            total_users = len(submission_users)
            for i, user in enumerate(submission_users):
                if i % max(1, total_users // 20) == 0 or i == total_users - 1:
                    progress = 65 + (i / total_users) * 30  # Progress from 65% to 95%
                    self.emit_progress(
                        f"Processing user {i+1}/{total_users} ({progress:.1f}%)", 
                        int(progress)
                    )
                
                try:
                    recommendations = self.generate_recommendations(
                        user,
                        full_history_with_details,
                        april_candidates,
                        april_popularity,
                        april_city_popularity,
                        full_frequency,
                        full_day_prefs,
                        april_day_patterns,
                        user_city,
                        event_city,
                        event_genre,
                        event_type
                    )
                    april_predictions[user] = recommendations
                except Exception as e:
                    print(f"Error for user {user}: {e}")
                    april_predictions[user] = []
            
            self.emit_progress("Recommendations generated for all users", 95)
            
            # 8. Create submission file
            self.emit_progress("Creating submission file...", 97)
            
            result = []
            for user in submission_users:
                items = april_predictions.get(user, [])
                item_str = ','.join(items)
                result.append({'user_id': user, 'item_ids': item_str})
            
            result_df = pd.DataFrame(result)
            result_df.to_csv(self.output_path, index=False, quoting=1)
            
            self.emit_progress("Submission file created successfully", 100)
            
            return self.output_path
            
        except Exception as e:
            self.emit_progress(f"Error in recommendation process: {str(e)}", 100)
            raise
    
    def get_event_city_mappings(self, df):
        """Extract city information for events from place_name and interactions"""
        event_city = {}
        event_place = {}
        
        for _, row in df.iterrows():
            item_id = row['item_id']
            city = row['city']
            place = row['place_name']
            
            # Store city and place information
            event_city[item_id] = city
            event_place[item_id] = place
        
        return event_city, event_place
    
    def calculate_popularity(self, interactions_df, candidate_events):
        """Calculate normalized popularity scores for candidate events"""
        event_counts = interactions_df['item_id'].value_counts().to_dict()
        total_interactions = sum(event_counts.values())
        
        if total_interactions > 0:
            popularity_scores = {event_id: event_counts.get(event_id, 0) / total_interactions 
                                for event_id in candidate_events}
        else:
            popularity_scores = {event_id: 0 for event_id in candidate_events}
        
        return popularity_scores
    
    def calculate_city_popularity(self, interactions_df, candidate_events):
        """Calculate city-specific popularity scores for candidate events"""
        city_event_pop = {}
        
        for city in interactions_df['city'].unique():
            if pd.isna(city):
                continue
                
            city_data = interactions_df[interactions_df['city'] == city]
            city_counts = city_data['item_id'].value_counts().to_dict()
            total = sum(city_counts.values()) if city_counts else 0
            
            if total > 0:
                city_event_pop[city] = {event_id: city_counts.get(event_id, 0) / total 
                                        for event_id in candidate_events}
            else:
                city_event_pop[city] = {event_id: 0 for event_id in candidate_events}
        
        return city_event_pop
    
    def extract_user_temporal_patterns(self, interactions_df):
        """
        Extract day of week preferences and attendance frequency for each user
        """
        # Add day of week column
        interactions_df['day_of_week'] = interactions_df['reservation_time'].dt.day_name()
        interactions_df['hour_of_day'] = interactions_df['reservation_time'].dt.hour
        interactions_df['month'] = interactions_df['reservation_time'].dt.month
        
        # Calculate user attendance frequency (events per month)
        user_monthly_frequency = {}
        user_day_preferences = {}
        user_hour_preferences = {}
        
        for user_id in interactions_df['user_id'].unique():
            user_data = interactions_df[interactions_df['user_id'] == user_id]
            
            # Calculate attendance frequency
            if len(user_data) > 0:
                min_date = user_data['reservation_time'].min()
                max_date = user_data['reservation_time'].max()
                
                if pd.notna(min_date) and pd.notna(max_date):
                    # Calculate months between first and last attendance
                    months_active = ((max_date.year - min_date.year) * 12 + 
                                    max_date.month - min_date.month + 1)
                    
                    if months_active > 0:
                        # Events per month
                        user_monthly_frequency[user_id] = len(user_data) / months_active
                    else:
                        # All in one month
                        user_monthly_frequency[user_id] = len(user_data)
                else:
                    user_monthly_frequency[user_id] = 0
            else:
                user_monthly_frequency[user_id] = 0
            
            # Calculate day of week preferences
            day_counts = user_data['day_of_week'].value_counts()
            total_days = day_counts.sum()
            
            if total_days > 0:
                user_day_preferences[user_id] = {day: count/total_days 
                                               for day, count in day_counts.items()}
            else:
                user_day_preferences[user_id] = {}
            
            # Calculate hour preferences
            hour_counts = user_data['hour_of_day'].value_counts()
            total_hours = hour_counts.sum()
            
            if total_hours > 0:
                user_hour_preferences[user_id] = {hour: count/total_hours 
                                                for hour, count in hour_counts.items()}
            else:
                user_hour_preferences[user_id] = {}
        
        return user_monthly_frequency, user_day_preferences, user_hour_preferences
    
    def extract_event_temporal_patterns(self, interactions_df, candidate_events):
        """Extract day of week and hour patterns for events"""
        # Add day of week if not already there
        if 'day_of_week' not in interactions_df.columns:
            interactions_df['day_of_week'] = interactions_df['reservation_time'].dt.day_name()
        if 'hour_of_day' not in interactions_df.columns:
            interactions_df['hour_of_day'] = interactions_df['reservation_time'].dt.hour
        
        event_day_patterns = {}
        event_hour_patterns = {}
        
        for item_id in candidate_events:
            item_data = interactions_df[interactions_df['item_id'] == item_id]
            
            # Day patterns
            if not item_data.empty:
                day_counts = item_data['day_of_week'].value_counts()
                total_days = day_counts.sum()
                
                if total_days > 0:
                    event_day_patterns[item_id] = {day: count/total_days 
                                                 for day, count in day_counts.items()}
                else:
                    event_day_patterns[item_id] = {}
                    
                # Hour patterns
                hour_counts = item_data['hour_of_day'].value_counts()
                total_hours = hour_counts.sum()
                
                if total_hours > 0:
                    event_hour_patterns[item_id] = {hour: count/total_hours 
                                                  for hour, count in hour_counts.items()}
                else:
                    event_hour_patterns[item_id] = {}
            else:
                event_day_patterns[item_id] = {}
                event_hour_patterns[item_id] = {}
        
        return event_day_patterns, event_hour_patterns
    
    def get_user_preferences(self, user_id, interactions_df, event_genre, event_type):
        """Get top genre and type preferences for a user"""
        user_data = interactions_df[interactions_df['user_id'] == user_id]
        
        if user_data.empty:
            return [], []
        
        # Extract genre preferences
        genre_counts = Counter()
        for _, row in user_data.iterrows():
            item_id = row['item_id']
            if item_id in event_genre and pd.notna(event_genre[item_id]):
                genre_counts[event_genre[item_id]] += 1
        
        # Extract type preferences
        type_counts = Counter()
        for _, row in user_data.iterrows():
            item_id = row['item_id']
            if item_id in event_type and pd.notna(event_type[item_id]):
                type_counts[event_type[item_id]] += 1
        
        # Get top preferences
        top_genres = [genre for genre, _ in genre_counts.most_common(3)]
        top_types = [t_type for t_type, _ in type_counts.most_common(2)]
        
        return top_genres, top_types
    
    def generate_recommendations(self, target_user, history_data, candidate_events, 
                               popularity_scores, city_popularity,
                               user_frequency, user_day_prefs, 
                               event_day_patterns, user_city, 
                               event_city, event_genre, event_type):
        """
        Generate recommendations for a user based on preferences, 
        frequency patterns, and day of week preferences
        """
        user_city_val = user_city.get(target_user)
        top_genres, top_types = self.get_user_preferences(target_user, history_data, event_genre, event_type)
        
        # Get user's frequency and day preferences
        monthly_frequency = user_frequency.get(target_user, 0)
        day_preferences = user_day_prefs.get(target_user, {})
        
        # Initialize scores
        event_scores = {}
        
        for event_id in candidate_events:
            score = 0
            event_city_val = event_city.get(event_id)
            event_genre_val = event_genre.get(event_id)
            event_type_val = event_type.get(event_id)
            event_day_pattern = event_day_patterns.get(event_id, {})
            
            # 1. Primary boost - genre and type match in user's city
            if user_city_val and event_city_val and user_city_val == event_city_val:
                if event_genre_val and event_genre_val in top_genres:
                    score += 6  # High score for genre match in user's city
                if event_type_val and event_type_val in top_types:
                    score += 4  # Medium score for type match in user's city
            
            # 2. Secondary boost - genre and type match in any city
            else:
                if event_genre_val and event_genre_val in top_genres:
                    score += 3  # Medium score for genre match
                if event_type_val and event_type_val in top_types:
                    score += 2  # Low score for type match
            
            # 3. Day of week preference boost
            day_match_score = 0
            for day, user_pref in day_preferences.items():
                if day in event_day_pattern:
                    # Match user's day preference with event's day pattern
                    day_match_score += user_pref * event_day_pattern[day]
            
            # Scale day match score and add to total
            score += day_match_score * 2
            
            # 4. Frequency-based adjustments
            if monthly_frequency > 0:
                # Adjust recommendations based on how often user attends events
                if monthly_frequency > 3:  # High frequency users (>3/month)
                    # For frequent attendees, prioritize variety and day matches
                    score = score * 1.2  # Boost preference matching
                    # Slightly reduce popularity influence
                    score += popularity_scores.get(event_id, 0) * 0.1
                elif monthly_frequency > 1:  # Medium frequency (1-3/month)
                    # Standard scoring
                    score += popularity_scores.get(event_id, 0) * 0.3
                else:  # Low frequency (<1/month)
                    # For infrequent attendees, give more weight to popular items
                    score += popularity_scores.get(event_id, 0) * 0.7
            else:
                # 5. Cold start - rely on popularity
                if user_city_val and event_city_val and user_city_val == event_city_val:
                    # City-specific popularity gets higher weight for cold start
                    city_pop = city_popularity.get(user_city_val, {}).get(event_id, 0)
                    score += city_pop * 3
                else:
                    # Global popularity as fallback
                    score += popularity_scores.get(event_id, 0) * 1.5
            
            # Store final score
            event_scores[event_id] = score
        
        # Sort by score and get top 10
        sorted_events = sorted(event_scores.items(), key=lambda x: x[1], reverse=True)
        top_events = [event_id for event_id, _ in sorted_events[:10]]
        
        return top_events
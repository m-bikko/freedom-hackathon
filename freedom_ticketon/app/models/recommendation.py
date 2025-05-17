import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity
import os
import pickle

class RecommendationModel:
    def __init__(self):
        self.train_data = None
        self.events_data = None
        self.user_item_matrix = None
        self.event_features = None
        self.model_ready = False
        self.progress = 0
        
    def load_data(self, train_path, events_path):
        """Load training and events data from CSV files"""
        self.train_data = pd.read_csv(train_path)
        self.events_data = pd.read_csv(events_path)
        self.progress = 10
        return True
        
    def preprocess_data(self):
        """Preprocess the data for recommendation model"""
        # Filter paid transactions
        self.train_data = self.train_data[self.train_data['sale_status'] == 'PAID']
        
        # Create user-item matrix (users who bought which events)
        user_items = self.train_data.groupby(['user_id', 'item_id']).size().reset_index(name='count')
        self.user_item_matrix = user_items.pivot(index='user_id', columns='item_id', values='count').fillna(0)
        
        # Extract event features (categories, genre, etc)
        self.events_data = self.events_data.fillna('')
        
        # Extract relevant features from events
        features_to_encode = ['film_genre', 'film_fcsk', 'film_type']
        for feature in features_to_encode:
            if feature in self.events_data.columns:
                self.events_data[feature] = self.events_data[feature].astype(str)
                
        # One-hot encoding for categorical features
        if 'film_genre' in self.events_data.columns:
            encoder = OneHotEncoder(sparse=False)
            genre_encoded = encoder.fit_transform(self.events_data[['film_genre']])
            genre_df = pd.DataFrame(
                genre_encoded, 
                columns=encoder.get_feature_names_out(['film_genre']),
                index=self.events_data.index
            )
            self.event_features = pd.concat([self.events_data[['item_id']], genre_df], axis=1)
            self.event_features = self.event_features.set_index('item_id')
        else:
            # Handle case where features are missing
            self.event_features = pd.DataFrame(index=self.events_data['item_id'])
        
        self.progress = 40
        return True
    
    def build_model(self):
        """Build recommendation model using content-based filtering"""
        # For content-based filtering we'll use event features
        
        # For each user, get their history
        user_histories = {}
        for user in self.user_item_matrix.index:
            user_histories[user] = self.user_item_matrix.loc[user][self.user_item_matrix.loc[user] > 0].index.tolist()
        
        # Compute event similarity matrix using cosine similarity
        if not self.event_features.empty and self.event_features.shape[1] > 0:
            event_sim_matrix = cosine_similarity(self.event_features)
            event_sim_df = pd.DataFrame(
                event_sim_matrix, 
                index=self.event_features.index, 
                columns=self.event_features.index
            )
        else:
            # Fallback to a basic model if features are missing
            event_ids = self.events_data['item_id'].unique()
            event_sim_df = pd.DataFrame(
                np.identity(len(event_ids)), 
                index=event_ids, 
                columns=event_ids
            )
        
        self.event_similarity = event_sim_df
        self.user_histories = user_histories
        self.model_ready = True
        self.progress = 80
        return True
    
    def make_recommendations(self, users, top_n=5):
        """Generate recommendations for given users"""
        recommendations = {}
        
        test_users = [u for u in users if u in self.user_item_matrix.index]
        new_users = [u for u in users if u not in self.user_item_matrix.index]
        
        # For existing users with history
        for user in test_users:
            if user in self.user_histories and self.user_histories[user]:
                user_items = self.user_histories[user]
                
                # Get similar events for each item in user history
                similar_items = []
                for item in user_items:
                    if item in self.event_similarity.index:
                        similar = self.event_similarity[item].sort_values(ascending=False)[1:top_n+1].index.tolist()
                        similar_items.extend(similar)
                
                # Count frequency of each recommendation
                rec_counter = {}
                for item in similar_items:
                    rec_counter[item] = rec_counter.get(item, 0) + 1
                
                # Sort by frequency
                sorted_recs = sorted(rec_counter.items(), key=lambda x: x[1], reverse=True)
                recommendations[user] = [item for item, _ in sorted_recs[:top_n]]
            else:
                recommendations[user] = []
        
        # For new users, recommend popular items
        if new_users:
            popular_items = self.train_data['item_id'].value_counts().index[:top_n].tolist()
            for user in new_users:
                recommendations[user] = popular_items
        
        self.progress = 100
        return recommendations
    
    def get_progress(self):
        """Get current progress of the model building process"""
        return self.progress
    
    def save_model(self, path):
        """Save the trained model to disk"""
        model_data = {
            'event_similarity': self.event_similarity,
            'user_histories': self.user_histories,
            'model_ready': self.model_ready
        }
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        return True
    
    def load_model(self, path):
        """Load a trained model from disk"""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        self.event_similarity = model_data['event_similarity']
        self.user_histories = model_data['user_histories']
        self.model_ready = model_data['model_ready']
        self.progress = 100 if self.model_ready else 0
        return True
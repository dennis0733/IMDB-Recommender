# src/data/database.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            # Load environment variables
            load_dotenv(dotenv_path='..\\..\\data\\.env')
            
            # Get MongoDB connection string
            mongo_uri = os.getenv('MONGO_URI')
            
            # Connect to MongoDB
            cls._instance.client = MongoClient(mongo_uri)
            cls._instance.db = cls._instance.client['imdb_recommender']
        return cls._instance
    
    def get_movies(self, query=None, limit=None):
        """Get movies from database with optional filtering"""
        if query is None:
            query = {}
        
        cursor = self.db.movies.find(query)
        
        if limit:
            cursor = cursor.limit(limit)
            
        return list(cursor)
    
    def get_series(self, query=None, limit=None):
        """Get TV series from database with optional filtering"""
        if query is None:
            query = {}
        
        cursor = self.db.series.find(query)
        
        if limit:
            cursor = cursor.limit(limit)
            
        return list(cursor)
    
    def get_movie_by_id(self, movie_id):
        """Get a movie by its ID"""
        return self.db.movies.find_one({"id": movie_id})
    
    def get_series_by_id(self, series_id):
        """Get a TV series by its ID"""
        return self.db.series.find_one({"id": series_id})
    
    def get_detailed_movie(self, movie_id):
        """Get detailed movie information by ID"""
        return self.db.detailed_movies.find_one({"id": movie_id})
    
    def get_detailed_series(self, series_id):
        """Get detailed series information by ID"""
        return self.db.detailed_series.find_one({"id": series_id})
    
    def get_movie_genres(self):
        """Get all movie genres"""
        return list(self.db.movie_genres.find())
    
    def get_tv_genres(self):
        """Get all TV genres"""
        return list(self.db.tv_genres.find())
    
    
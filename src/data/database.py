# src/data/database.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            try:
                # Get MongoDB connection string directly from environment
                mongo_uri = os.getenv('MONGO_URI')
                print(f"Attempting MongoDB connection with URI starting with: {mongo_uri[:15] if mongo_uri else 'None'}...")
                
                if not mongo_uri:
                    print("MongoDB URI is not set in environment variables!")
                    raise ValueError("MONGO_URI environment variable is not set")
                
                # Connect to MongoDB with timeout
                cls._instance.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                
                # Test connection
                cls._instance.client.admin.command('ping')
                print("MongoDB connection successful!")
                
                # Connect to database
                cls._instance.db = cls._instance.client['imdb_recommender']
                
                # Print available collections
                collections = cls._instance.db.list_collection_names()
                print(f"Available collections: {collections}")
                
                # Check if main collections exist and contain data
                movie_count = cls._instance.db.detailed_movies.count_documents({})
                series_count = cls._instance.db.detailed_series.count_documents({})
                print(f"Found {movie_count} movies and {series_count} series in database")
                
            except Exception as e:
                print(f"MongoDB connection error: {str(e)}")
                # Re-raise the exception to indicate failure
                raise
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
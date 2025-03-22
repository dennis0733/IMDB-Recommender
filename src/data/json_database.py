# src/data/json_database.py
import json
import os

class JSONDatabase:
    """
    Database class that uses JSON files instead of MongoDB
    Implements a singleton pattern to avoid reloading data on every request
    """
    _instance = None  # Class variable to hold the singleton instance
    _is_initialized = False  # Flag to check if data has been loaded
    
    def __new__(cls, data_dir="data/processed"):
        # Create a singleton instance
        if cls._instance is None:
            cls._instance = super(JSONDatabase, cls).__new__(cls)
            cls._instance.data_dir = data_dir
            cls._instance.collections = {}
            cls._instance._is_initialized = False
        return cls._instance
    
    def __init__(self, data_dir="data/processed"):
        # Only initialize data once, even if __init__ is called multiple times
        if not self._is_initialized:
            self.data_dir = data_dir
            self._load_collections()
            self._is_initialized = True
    
    def _load_collections(self):
        """Load all JSON files from data directory"""
        try:
            print(f"Looking for JSON files in: {self.data_dir}")
            files_in_dir = os.listdir(self.data_dir)
            print(f"Found files: {files_in_dir}")
            # Load detailed movies
            movies_path = os.path.join(self.data_dir, "imdb_recommender.detailed_movies.json")
            if os.path.exists(movies_path):
                with open(movies_path, 'r', encoding='utf-8') as f:
                    self.collections["detailed_movies"] = json.load(f)
                print(f"Loaded {len(self.collections['detailed_movies'])} detailed movies")
            
            # Load detailed series
            series_path = os.path.join(self.data_dir, "imdb_recommender.detailed_series.json")
            if os.path.exists(series_path):
                with open(series_path, 'r', encoding='utf-8') as f:
                    self.collections["detailed_series"] = json.load(f)
                print(f"Loaded {len(self.collections['detailed_series'])} detailed series")
            
            # Load movie genres
            movie_genres_path = os.path.join(self.data_dir, "imdb_recommender.movie_genres.json")
            if os.path.exists(movie_genres_path):
                with open(movie_genres_path, 'r', encoding='utf-8') as f:
                    self.collections["movie_genres"] = json.load(f)
                print(f"Loaded {len(self.collections['movie_genres'])} movie genres")
            
            # Load TV genres
            tv_genres_path = os.path.join(self.data_dir, "imdb_recommender.tv_genres.json")
            if os.path.exists(tv_genres_path):
                with open(tv_genres_path, 'r', encoding='utf-8') as f:
                    self.collections["tv_genres"] = json.load(f)
                print(f"Loaded {len(self.collections['tv_genres'])} TV genres")
            
            # Load other collections if needed
            movies_path = os.path.join(self.data_dir, "imdb_recommender.movies.json")
            if os.path.exists(movies_path):
                with open(movies_path, 'r', encoding='utf-8') as f:
                    self.collections["movies"] = json.load(f)
                print(f"Loaded {len(self.collections['movies'])} movies")
                
            series_path = os.path.join(self.data_dir, "imdb_recommender.series.json")
            if os.path.exists(series_path):
                with open(series_path, 'r', encoding='utf-8') as f:
                    self.collections["series"] = json.load(f)
                print(f"Loaded {len(self.collections['series'])} series")
                
            # Create an ID-based index for faster lookups
            self._create_indexes()
                
        except Exception as e:
            print(f"Error loading collections: {e}")
    
    def _create_indexes(self):
        """Create indexes for faster lookups by ID"""
        self.indexes = {}
        
        # Create index for detailed movies
        if "detailed_movies" in self.collections:
            self.indexes["detailed_movies"] = {}
            for i, movie in enumerate(self.collections["detailed_movies"]):
                if "id" in movie:
                    # Convert ID to string for consistent lookup
                    movie_id = str(movie["id"])
                    self.indexes["detailed_movies"][movie_id] = i
        
        # Create index for detailed series
        if "detailed_series" in self.collections:
            self.indexes["detailed_series"] = {}
            for i, series in enumerate(self.collections["detailed_series"]):
                if "id" in series:
                    # Convert ID to string for consistent lookup
                    series_id = str(series["id"])
                    self.indexes["detailed_series"][series_id] = i
    
    def get_collection(self, collection_name):
        """Get a collection by name"""
        return self.collections.get(collection_name, [])
    
    def get_detailed_movie(self, movie_id):
        """Get detailed movie by ID - using index for faster lookup"""
        # Convert ID to string for consistent comparison
        movie_id_str = str(movie_id)
        
        # Check if we have an index for this collection
        if "detailed_movies" in self.indexes and movie_id_str in self.indexes["detailed_movies"]:
            # Get the movie directly from the index
            idx = self.indexes["detailed_movies"][movie_id_str]
            return self.collections["detailed_movies"][idx]
        
        # Fallback to linear search if not found in index
        movies = self.collections.get("detailed_movies", [])
        for movie in movies:
            if str(movie.get("id", "")) == movie_id_str:
                return movie
        
        return None
    
    def get_detailed_series(self, series_id):
        """Get detailed series by ID - using index for faster lookup"""
        # Convert ID to string for consistent comparison
        series_id_str = str(series_id)
        
        # Check if we have an index for this collection
        if "detailed_series" in self.indexes and series_id_str in self.indexes["detailed_series"]:
            # Get the series directly from the index
            idx = self.indexes["detailed_series"][series_id_str]
            return self.collections["detailed_series"][idx]
        
        # Fallback to linear search if not found in index
        series_list = self.collections.get("detailed_series", [])
        for series in series_list:
            if str(series.get("id", "")) == series_id_str:
                return series
        
        return None
    
    def find(self, collection_name, query=None, limit=None):
        """Simplified find method similar to MongoDB"""
        data = self.get_collection(collection_name)
        
        if query is None:
            results = data
        else:
            results = []
            for item in data:
                match = True
                for key, value in query.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                if match:
                    results.append(item)
        
        if limit and limit > 0:
            return results[:limit]
        return results
    
    def find_one(self, collection_name, query):
        """Find a single document"""
        results = self.find(collection_name, query, limit=1)
        if results:
            return results[0]
        return None
    
    def reset(self):
        """Reset the database (useful for testing)"""
        self._is_initialized = False
        self.collections = {}
        self.indexes = {}
        self._load_collections()
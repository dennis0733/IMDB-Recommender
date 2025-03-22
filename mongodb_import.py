import json
import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

def remove_duplicates(data_list):
    """
    Remove duplicate entries from a list of dictionaries
    that may contain unhashable types like lists
    """
    if not data_list or len(data_list) <= 1:
        return data_list
    
    # Convert JSON to strings for comparison (handles unhashable types)
    string_records = [json.dumps(record, sort_keys=True) for record in data_list]
    
    # Create a DataFrame with the string representation
    df = pd.DataFrame({'json_str': string_records, 'original_index': range(len(data_list))})
    
    # Count before deduplication
    count_before = len(df)
    
    # Remove duplicates based on string representation
    df_no_duplicates = df.drop_duplicates(subset=['json_str'], keep='first')
    
    # Count after deduplication
    count_after = len(df_no_duplicates)
    count_removed = count_before - count_after
    
    if count_removed > 0:
        print(f"Removed {count_removed} duplicates out of {count_before} entries")
    else:
        print("No duplicates found!")
    
    # Get the indices of records to keep
    indices_to_keep = df_no_duplicates['original_index'].tolist()
    
    # Use the indices to get the original records
    deduplicated_data = [data_list[i] for i in indices_to_keep]
    
    return deduplicated_data

def import_data_to_mongodb():
    # Load environment variables
    load_dotenv(dotenv_path="data\\.env")
    
    # Get MongoDB connection string from environment variables
    mongo_uri = os.getenv('MONGO_URI')
    
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client['imdb_recommender']
    
    # Create collections
    movies_collection = db['movies']
    series_collection = db['series']
    movie_genres_collection = db['movie_genres']
    tv_genres_collection = db['tv_genres']
    
    # Import movies
    print("Importing movies...")
    with open('data/raw_data/movies.json', 'r', encoding='utf-8') as f:
        movies_data = json.load(f)
    
    if movies_data:
        print(f"Original movie count: {len(movies_data)}")
        # Remove duplicates
        movies_data = remove_duplicates(movies_data)
        print(f"Deduplicated movie count: {len(movies_data)}")
        
        # Clear existing data
        movies_collection.delete_many({})
        # Insert new data
        movies_collection.insert_many(movies_data)
        print(f"Imported {len(movies_data)} movies")
    
    # Import TV series
    print("Importing TV series...")
    with open('data/raw_data/tv_series.json', 'r', encoding='utf-8') as f:
        series_data = json.load(f)
    
    if series_data:
        print(f"Original TV series count: {len(series_data)}")
        # Remove duplicates
        series_data = remove_duplicates(series_data)
        print(f"Deduplicated TV series count: {len(series_data)}")
        
        # Clear existing data
        series_collection.delete_many({})
        # Insert new data
        series_collection.insert_many(series_data)
        print(f"Imported {len(series_data)} TV series")
    
    # Import movie genres
    print("Importing movie genres...")
    with open('data/raw_data/movie_genres.json', 'r', encoding='utf-8') as f:
        movie_genres_data = json.load(f)
    
    if 'genres' in movie_genres_data:
        movie_genres = movie_genres_data['genres']
        print(f"Original movie genres count: {len(movie_genres)}")
        # Remove duplicates
        movie_genres = remove_duplicates(movie_genres)
        print(f"Deduplicated movie genres count: {len(movie_genres)}")
        
        # Clear existing data
        movie_genres_collection.delete_many({})
        # Insert new data
        movie_genres_collection.insert_many(movie_genres)
        print(f"Imported {len(movie_genres)} movie genres")
    
    # Import TV genres
    print("Importing TV genres...")
    with open('data/raw_data/tv_genres.json', 'r', encoding='utf-8') as f:
        tv_genres_data = json.load(f)
    
    if 'genres' in tv_genres_data:
        tv_genres = tv_genres_data['genres']
        print(f"Original TV genres count: {len(tv_genres)}")
        # Remove duplicates
        tv_genres = remove_duplicates(tv_genres)
        print(f"Deduplicated TV genres count: {len(tv_genres)}")
        
        # Clear existing data
        tv_genres_collection.delete_many({})
        # Insert new data
        tv_genres_collection.insert_many(tv_genres)
        print(f"Imported {len(tv_genres)} TV genres")
    
    # Import detailed movie data
    if os.path.exists('data/raw_data/detailed_movies.json'):
        print("Importing detailed movie data...")
        with open('data/raw_data/detailed_movies.json', 'r', encoding='utf-8') as f:
            detailed_movies = json.load(f)
        
        if detailed_movies:
            print(f"Original detailed movies count: {len(detailed_movies)}")
            # Remove duplicates
            detailed_movies = remove_duplicates(detailed_movies)
            print(f"Deduplicated detailed movies count: {len(detailed_movies)}")
            
            detailed_movies_collection = db['detailed_movies']
            # Clear existing data
            detailed_movies_collection.delete_many({})
            # Insert new data
            detailed_movies_collection.insert_many(detailed_movies)
            print(f"Imported {len(detailed_movies)} detailed movies")
    
    # Import detailed series data
    if os.path.exists('data/raw_data/detailed_series.json'):
        print("Importing detailed series data...")
        with open('data/raw_data/detailed_series.json', 'r', encoding='utf-8') as f:
            detailed_series = json.load(f)
        
        if detailed_series:
            print(f"Original detailed series count: {len(detailed_series)}")
            # Remove duplicates
            detailed_series = remove_duplicates(detailed_series)
            print(f"Deduplicated detailed series count: {len(detailed_series)}")
            
            detailed_series_collection = db['detailed_series']
            # Clear existing data
            detailed_series_collection.delete_many({})
            # Insert new data
            detailed_series_collection.insert_many(detailed_series)
            print(f"Imported {len(detailed_series)} detailed series")
    
    print("Import complete!")

if __name__ == "__main__":
    import_data_to_mongodb()
# web/routes/recommender.py
from flask import Blueprint, render_template, request, jsonify, current_app
import joblib
import os
import sys
import pandas as pd

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.content_based import get_movie_recommendations, get_series_recommendations
from src.data.database import Database  # Import your existing Database class

# Create blueprint
recommender_bp = Blueprint('recommender', __name__)

# Load recommendation models
movie_model = None
series_model = None
db_instance = None

def load_models():
    global movie_model, series_model, db_instance
    try:
        model_path = current_app.config['MODEL_PATH']
        movie_model = joblib.load(os.path.join(model_path, 'movie_recommender.joblib'))
        series_model = joblib.load(os.path.join(model_path, 'series_recommender.joblib'))
        print("Recommendation models loaded successfully")
        
        # Initialize MongoDB connection using your Database class
        try:
            db_instance = Database()
            print("MongoDB connection established")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
    except Exception as e:
        print(f"Error loading recommendation models: {e}")

# Use before_request instead of before_app_first_request
@recommender_bp.before_request
def initialize():
    global movie_model, series_model, db_instance
    if movie_model is None or series_model is None or db_instance is None:
        load_models()

# Update the index route in recommender.py

@recommender_bp.route('/')
def index():
    # Get some popular movies and series for the homepage
    popular_movies = []
    popular_series = []
    
    if movie_model:
        movies_df = movie_model['movies_df']
        
        # Calculate a combined score of popularity and rating
        try:
            # Calculate combined score
            movies_df['combined_score'] = (
                (movies_df['popularity_scaled'] * movies_df['vote_average_scaled'] * movies_df['vote_count_scaled'] 
                ) )
            
            # Get top 6 movies by combined score
            top_movies = movies_df.sort_values('combined_score', ascending=False).head(12)
            
            # Filter out movies with no poster
            top_movies = top_movies[top_movies['poster_path'].notna()]
            
            # Take the top 6 that have posters
            top_movies = top_movies.head(6)
            
            print(f"Selected top 6 movies with scores ranging from {top_movies['combined_score'].min():.2f} to {top_movies['combined_score'].max():.2f}")
        except Exception as e:
            print(f"Error calculating combined scores for movies: {e}")
            # Fallback to original method
            top_movies = movies_df.sort_values('popularity', ascending=False).head(6)
        
        for _, movie in top_movies.iterrows():
            # Try to get enhanced data from MongoDB
            enhanced_movie = None
            if db_instance:
                try:
                    enhanced_movie = db_instance.get_detailed_movie(movie['id'])
                except Exception as e:
                    print(f"Error fetching movie from MongoDB: {e}")
            
            # Create movie data for display
            movie_data = {
                'id': movie['id'],
                'title': movie['title'],
                'poster_path': movie['poster_path'],
                'vote_average': movie['vote_average'],
                'genres': movie['genre_names'] if isinstance(movie['genre_names'], list) else []
            }
            
            # Update with enhanced data if available
            if enhanced_movie:
                # Keep basic info from model but get extra details from MongoDB
                if 'genre_names' in enhanced_movie and enhanced_movie['genre_names']:
                    movie_data['genres'] = enhanced_movie['genre_names']
                if 'poster_path' in enhanced_movie and enhanced_movie['poster_path']:
                    movie_data['poster_path'] = enhanced_movie['poster_path']
            
            popular_movies.append(movie_data)
    
    if series_model:
        series_df = series_model['series_df']
        
        # Calculate a combined score of popularity and rating
        try:
            
            
            # Calculate combined score
            series_df['combined_score'] = (
                (series_df['popularity_scaled'] * series_df['vote_average_scaled'] * series_df['vote_count_scaled'] 
                ) )
            
            
            # Get top 6 series by combined score
            top_series = series_df.sort_values('combined_score', ascending=False).head(12)
            
            # Filter out series with no poster
            top_series = top_series[top_series['poster_path'].notna()]
            
            # Take the top 6 that have posters
            top_series = top_series.head(6)
            
            print(f"Selected top 6 series with scores ranging from {top_series['combined_score'].min():.2f} to {top_series['combined_score'].max():.2f}")
        except Exception as e:
            print(f"Error calculating combined scores for series: {e}")
            # Fallback to original method
            top_series = series_df.sort_values('popularity', ascending=False).head(6)
        
        for _, series in top_series.iterrows():
            # Try to get enhanced data from MongoDB
            enhanced_series = None
            if db_instance:
                try:
                    enhanced_series = db_instance.get_detailed_series(series['id'])
                except Exception as e:
                    print(f"Error fetching series from MongoDB: {e}")
                    
            # Create series data for display
            series_data = {
                'id': series['id'],
                'title': series['name'],
                'poster_path': series['poster_path'],
                'vote_average': series['vote_average'],
                'genres': series['genre_names'] if isinstance(series['genre_names'], list) else []
            }
            
            # Update with enhanced data if available
            if enhanced_series:
                # Keep basic info from model but get extra details from MongoDB
                if 'genre_names' in enhanced_series and enhanced_series['genre_names']:
                    series_data['genres'] = enhanced_series['genre_names']
                if 'poster_path' in enhanced_series and enhanced_series['poster_path']:
                    series_data['poster_path'] = enhanced_series['poster_path']
            
            popular_series.append(series_data)
    
    return render_template('index.html', 
                           popular_movies=popular_movies,
                           popular_series=popular_series)


@recommender_bp.route('/search')
def search():
    query = request.args.get('query', '').strip().lower()
    category = request.args.get('category', 'all')  # 'movies', 'series', or 'all'
    
    results = []
    
    if query:
        if category in ['all', 'movies'] and movie_model:
            # Search movies by title or genre
            movies_df = movie_model['movies_df']
            
            # Create a mask for title matches
            title_mask = movies_df['title'].str.lower().str.contains(query, case=False, na=False)
            
            # Create a mask for genre matches
            genre_mask = movies_df['genre_names'].apply(
                lambda genres: any(query in genre.lower() for genre in genres) if isinstance(genres, list) else False
            )
            
            # Combine masks with OR operator
            combined_mask = title_mask | genre_mask
            
            # Apply the combined mask to get results
            movie_results = movies_df[combined_mask]
            
            for _, movie in movie_results.iterrows():
                genres = movie['genre_names'] if isinstance(movie['genre_names'], list) else []
                
                # Try to get enhanced data from MongoDB
                enhanced_movie = None
                if db_instance:
                    try:
                        enhanced_movie = db_instance.get_detailed_movie(movie['id'])
                    except Exception as e:
                        print(f"Error fetching movie from MongoDB in search: {e}")
                
                # Create basic movie data
                movie_data = {
                    'id': movie['id'],
                    'title': movie['title'],
                    'poster_path': movie['poster_path'],
                    'vote_average': movie['vote_average'],
                    'genres': genres,
                    'type': 'movie'
                }
                
                # Update with enhanced data if available
                if enhanced_movie:
                    if 'genre_names' in enhanced_movie and enhanced_movie['genre_names']:
                        movie_data['genres'] = enhanced_movie['genre_names']
                    if 'poster_path' in enhanced_movie and enhanced_movie['poster_path']:
                        movie_data['poster_path'] = enhanced_movie['poster_path']
                    if 'vote_average' in enhanced_movie:
                        movie_data['vote_average'] = enhanced_movie['vote_average']
                
                results.append(movie_data)
        
        if category in ['all', 'series'] and series_model:
            # Search series by title or genre
            series_df = series_model['series_df']
            
            # Create a mask for title matches
            title_mask = series_df['name'].str.lower().str.contains(query, case=False, na=False)
            
            # Create a mask for genre matches
            genre_mask = series_df['genre_names'].apply(
                lambda genres: any(query in genre.lower() for genre in genres) if isinstance(genres, list) else False
            )
            
            # Combine masks with OR operator
            combined_mask = title_mask | genre_mask
            
            # Apply the combined mask to get results
            series_results = series_df[combined_mask]
            
            for _, series in series_results.iterrows():
                genres = series['genre_names'] if isinstance(series['genre_names'], list) else []
                
                # Try to get enhanced data from MongoDB
                enhanced_series = None
                if db_instance:
                    try:
                        enhanced_series = db_instance.get_detailed_series(series['id'])
                    except Exception as e:
                        print(f"Error fetching series from MongoDB in search: {e}")
                
                # Create basic series data
                series_data = {
                    'id': series['id'],
                    'title': series['name'],
                    'poster_path': series['poster_path'],
                    'vote_average': series['vote_average'],
                    'genres': genres,
                    'type': 'series'
                }
                
                # Update with enhanced data if available
                if enhanced_series:
                    if 'genre_names' in enhanced_series and enhanced_series['genre_names']:
                        series_data['genres'] = enhanced_series['genre_names']
                    if 'poster_path' in enhanced_series and enhanced_series['poster_path']:
                        series_data['poster_path'] = enhanced_series['poster_path']
                    if 'vote_average' in enhanced_series:
                        series_data['vote_average'] = enhanced_series['vote_average']
                
                results.append(series_data)
    
    return render_template('search.html', query=query, results=results)

# Updated route functions for movie_recommender and series_recommender

@recommender_bp.route('/movie_recommender')
def movie_recommender():
    """Landing page for movie recommendations with a search form"""
    # Get popular movies using the same algorithm as the homepage
    popular_movies = []
    
    if movie_model:
        movies_df = movie_model['movies_df']
        
        # Calculate a combined score of popularity and rating
        try:
            
            # Calculate combined score
            movies_df['combined_score'] = (
                (movies_df['popularity_scaled'] * movies_df['vote_average_scaled'] * movies_df['vote_count_scaled'] 
                ) )
            
            # Get top movies by combined score
            top_movies = movies_df.sort_values('combined_score', ascending=False).head(20)
            
            # Filter out movies with no poster
            top_movies = top_movies[top_movies['poster_path'].notna()]
            
            # Take exactly 9 that have posters to fit 3x3 grid
            top_movies = top_movies.head(9)
            
            print(f"Selected top 9 movies with scores ranging from {top_movies['combined_score'].min():.2f} to {top_movies['combined_score'].max():.2f}")
        except Exception as e:
            print(f"Error calculating combined scores for movies: {e}")
            # Fallback to original method
            top_movies = movies_df.sort_values('popularity', ascending=False).head(9)
        
        for _, movie in top_movies.iterrows():
            # Try to get enhanced data from MongoDB
            enhanced_movie = None
            if db_instance:
                try:
                    enhanced_movie = db_instance.get_detailed_movie(movie['id'])
                except Exception as e:
                    print(f"Error fetching movie from MongoDB: {e}")
            
            # Create movie data for display
            movie_data = {
                'id': movie['id'],
                'title': movie['title'],
                'poster_path': movie['poster_path'],
                'vote_average': movie['vote_average'],
                'genres': movie['genre_names'] if isinstance(movie['genre_names'], list) else []
            }
            
            # Update with enhanced data if available
            if enhanced_movie:
                # Keep basic info from model but get extra details from MongoDB
                if 'genre_names' in enhanced_movie and enhanced_movie['genre_names']:
                    movie_data['genres'] = enhanced_movie['genre_names']
                if 'poster_path' in enhanced_movie and enhanced_movie['poster_path']:
                    movie_data['poster_path'] = enhanced_movie['poster_path']
            
            popular_movies.append(movie_data)
    
    return render_template('movie_recommender_landing.html', popular_movies=popular_movies)

@recommender_bp.route('/series_recommender')
def series_recommender():
    """Landing page for series recommendations with a search form"""
    # Get popular series using the same algorithm as the homepage
    popular_series = []
    
    if series_model:
        series_df = series_model['series_df']
        
        # Calculate a combined score of popularity and rating
        try:
            
            
            # Get top series by combined score
            top_series = series_df.sort_values('combined_score', ascending=False).head(20)
            
            # Filter out series with no poster
            top_series = top_series[top_series['poster_path'].notna()]
            
            # Take exactly 9 that have posters to fit 3x3 grid
            top_series = top_series.head(9)
            
            print(f"Selected top 9 series with scores ranging from {top_series['combined_score'].min():.2f} to {top_series['combined_score'].max():.2f}")
        except Exception as e:
            print(f"Error calculating combined scores for series: {e}")
            # Fallback to original method
            top_series = series_df.sort_values('popularity', ascending=False).head(9)
        
        for _, series in top_series.iterrows():
            # Try to get enhanced data from MongoDB
            enhanced_series = None
            if db_instance:
                try:
                    enhanced_series = db_instance.get_detailed_series(series['id'])
                except Exception as e:
                    print(f"Error fetching series from MongoDB: {e}")
                    
            # Create series data for display
            series_data = {
                'id': series['id'],
                'title': series['name'],
                'poster_path': series['poster_path'],
                'vote_average': series['vote_average'],
                'genres': series['genre_names'] if isinstance(series['genre_names'], list) else []
            }
            
            # Update with enhanced data if available
            if enhanced_series:
                # Keep basic info from model but get extra details from MongoDB
                if 'genre_names' in enhanced_series and enhanced_series['genre_names']:
                    series_data['genres'] = enhanced_series['genre_names']
                if 'poster_path' in enhanced_series and enhanced_series['poster_path']:
                    series_data['poster_path'] = enhanced_series['poster_path']
            
            popular_series.append(series_data)
    
    return render_template('series_recommender_landing.html', popular_series=popular_series)

@recommender_bp.route('/movie/<movie_id>')
def movie_detail(movie_id):
    """Get details for a specific movie and provide recommendations"""
    if not movie_model:
        load_models()
        if not movie_model:
            return "Movie recommendation model not loaded", 500
    
    # For debugging
    print(f"\n==== DEBUG: Looking for movie ID: {movie_id} ====")
    
    # First try to get the movie directly from MongoDB
    complete_movie = None
    if db_instance:
        try:
            # Convert ID to appropriate type if needed
            if movie_id.isdigit():
                # If ID is numeric, try both string and integer versions
                mongo_movie = db_instance.get_detailed_movie(movie_id)
                if not mongo_movie:
                    mongo_movie = db_instance.get_detailed_movie(int(movie_id))
            else:
                mongo_movie = db_instance.get_detailed_movie(movie_id)
                
            if mongo_movie:
                # MongoDB returns ObjectId which is not JSON serializable
                if '_id' in mongo_movie:
                    mongo_movie.pop('_id', None)
                print(f"Found movie directly in MongoDB: {mongo_movie.get('title', 'Unknown')}")
                complete_movie = mongo_movie
                
                # Process genres properly
                if 'genre_names' not in complete_movie or not complete_movie['genre_names']:
                    # Try to extract genres from other fields
                    if 'genres' in complete_movie and complete_movie['genres']:
                        genres = complete_movie['genres']
                        extracted_genres = []
                        
                        if isinstance(genres, list):
                            for genre in genres:
                                if isinstance(genre, dict) and 'name' in genre:
                                    extracted_genres.append(genre['name'])
                                elif isinstance(genre, str):
                                    extracted_genres.append(genre)
                        
                        complete_movie['genre_names'] = extracted_genres
                        print(f"Extracted genres: {extracted_genres}")
            else:
                print(f"Movie not found in MongoDB, falling back to model dataframe")
        except Exception as e:
            print(f"Error fetching movie from MongoDB: {e}")
    
    # If we couldn't get the movie from MongoDB, fall back to the model dataframe
    if complete_movie is None:
        movies_df = movie_model['movies_df']
        
        # First try exact match (highest priority)
        movie = None
        
        # Try string format
        try:
            movie_id_str = str(movie_id)
            result = movies_df[movies_df['id'].astype(str) == movie_id_str]
            if not result.empty:
                movie = result.iloc[0].to_dict()
                print(f"Found movie using string comparison: {movie['title']}")
        except Exception as e:
            print(f"Error in string comparison: {e}")
        
        # Try integer format
        if movie is None and isinstance(movie_id, str) and movie_id.isdigit():
            try:
                movie_id_int = int(movie_id)
                result = movies_df[movies_df['id'] == movie_id_int]
                if not result.empty:
                    movie = result.iloc[0].to_dict()
                    print(f"Found movie using integer comparison: {movie['title']}")
            except Exception as e:
                print(f"Error in integer comparison: {e}")
        
        # Last resort: check all rows
        if movie is None:
            print("Trying manual search...")
            for i, row in movies_df.iterrows():
                # Limit debug output
                if i % 1000 == 0:
                    print(f"Checking row {i}...")
                    
                if str(row['id']) == str(movie_id):
                    movie = row.to_dict()
                    print(f"Found movie through manual search: {movie['title']}")
                    break
        
        # If movie still not found
        if movie is None:
            print(f"Movie with ID {movie_id} not found after all attempts")
            print(f"Sample IDs in dataset: {movies_df['id'].head(10).tolist()}")
            print(f"ID types in dataset: {movies_df['id'].apply(type).unique()}")
            return render_template('404.html'), 404
        
        # Try to get enhanced data from MongoDB
        enhanced_movie = None
        if db_instance:
            try:
                print(f"Looking for enhanced data in MongoDB for movie ID: {movie['id']}")
                enhanced_movie = db_instance.get_detailed_movie(movie['id'])
                if enhanced_movie:
                    # MongoDB returns ObjectId which is not JSON serializable
                    if '_id' in enhanced_movie:
                        enhanced_movie.pop('_id', None)
                    print(f"Found enhanced data in MongoDB for {movie['title']}")
                else:
                    print(f"No enhanced data found in MongoDB for {movie['title']}")
            except Exception as e:
                print(f"Error fetching movie from MongoDB: {e}")
        
        # Merge model data with MongoDB data if available
        if enhanced_movie:
            # Start with enhanced data as the base
            complete_movie = enhanced_movie
            # Ensure the core fields from the model are preserved
            complete_movie['title'] = movie['title']
            complete_movie['id'] = movie['id']
            
            # Make sure to get genres from model data if not in MongoDB
            if ('genre_names' not in complete_movie or not complete_movie['genre_names']) and 'genre_names' in movie:
                complete_movie['genre_names'] = movie['genre_names']
                
            # Process genres if still missing
            if 'genre_names' not in complete_movie or not complete_movie['genre_names']:
                if 'genres' in complete_movie and complete_movie['genres']:
                    genres = complete_movie['genres']
                    extracted_genres = []
                    
                    if isinstance(genres, list):
                        for genre in genres:
                            if isinstance(genre, dict) and 'name' in genre:
                                extracted_genres.append(genre['name'])
                            elif isinstance(genre, str):
                                extracted_genres.append(genre)
                    
                    complete_movie['genre_names'] = extracted_genres
                    print(f"Extracted genres: {extracted_genres}")
        else:
            complete_movie = movie
    
    # Ensure we have an ID for recommendations
    movie_id_for_recs = complete_movie.get('id', movie_id)
    movie_title = complete_movie.get('title', 'Unknown')
    
    # Add missing fields with default values to ensure template rendering works
    required_fields = {
        'genre_names': [],
        'vote_average': 0.0,
        'popularity': 0.0,
        'poster_path': None,
        'overview': '',
        'release_date': '',
        'vote_count': 0,
        'runtime': 0,
        'budget': 0,
        'revenue': 0,
        'backdrop_path': None,
        'original_language': '',
        'production_companies': []
    }
    
    # Check if fields exist and add default values for missing ones
    for field, default_value in required_fields.items():
        if field not in complete_movie or complete_movie[field] is None:
            print(f"Adding missing field '{field}' with default value")
            complete_movie[field] = default_value
    
    # Ensure genre_names is a list and not None
    if complete_movie['genre_names'] is None:
        complete_movie['genre_names'] = []
        
    # Debug genre names
    print(f"Final genre_names: {complete_movie.get('genre_names', [])}")
    
    # Get recommendations 
    try:
        # Fall back to title-based method
        print(f"Using title-based recommendation for movie: {movie_title}")
        recommendations = get_movie_recommendations(movie_title, movie_model, top_n=9)
        
        # Enhance recommendations with MongoDB data if available
        if db_instance:
            enhanced_recommendations = []
            for rec in recommendations:
                try:
                    # Look for enhanced data
                    enhanced_rec = db_instance.get_detailed_movie(rec['id'])
                    if enhanced_rec:
                        # MongoDB returns ObjectId which is not JSON serializable
                        if '_id' in enhanced_rec:
                            enhanced_rec.pop('_id', None)
                        # Merge model recommendation with enhanced data
                        merged_rec = {**rec, **enhanced_rec}
                        # Ensure core fields are preserved
                        merged_rec['title'] = rec['title']
                        merged_rec['id'] = rec['id']
                        merged_rec['similarity'] = rec['similarity']
                        
                        # Process genres for recommendations too
                        if 'genre_names' not in merged_rec or not merged_rec['genre_names']:
                            if 'genres' in merged_rec and merged_rec['genres']:
                                genres = merged_rec['genres']
                                extracted_genres = []
                                
                                if isinstance(genres, list):
                                    for genre in genres:
                                        if isinstance(genre, dict) and 'name' in genre:
                                            extracted_genres.append(genre['name'])
                                        elif isinstance(genre, str):
                                            extracted_genres.append(genre)
                                
                                merged_rec['genre_names'] = extracted_genres
                        
                        enhanced_recommendations.append(merged_rec)
                    else:
                        enhanced_recommendations.append(rec)
                except Exception as e:
                    print(f"Error enhancing recommendation: {e}")
                    enhanced_recommendations.append(rec)
            
            # Replace recommendations with enhanced ones
            if enhanced_recommendations:
                recommendations = enhanced_recommendations
        
        # Ensure each recommendation has all required fields
        for rec in recommendations:
            for field, default_value in required_fields.items():
                if field not in rec or rec[field] is None:
                    rec[field] = default_value
                    
        print(f"Generated {len(recommendations)} recommendations")
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        recommendations = []
    
    return render_template('movie_recommender.html', movie=complete_movie, recommendations=recommendations)

@recommender_bp.route('/series/<series_id>')
def series_detail(series_id):
    """Get details for a specific TV series and provide recommendations"""
    if not series_model:
        load_models()
        if not series_model:
            return "Series recommendation model not loaded", 500
    
    # For debugging
    print(f"\n==== DEBUG: Looking for series ID: {series_id} ====")
    
    # First try to get the series directly from MongoDB
    complete_series = None
    if db_instance:
        try:
            # Convert ID to appropriate type if needed
            if series_id.isdigit():
                # If ID is numeric, try both string and integer versions
                mongo_series = db_instance.get_detailed_series(series_id)
                if not mongo_series:
                    mongo_series = db_instance.get_detailed_series(int(series_id))
            else:
                mongo_series = db_instance.get_detailed_series(series_id)
                
            if mongo_series:
                # MongoDB returns ObjectId which is not JSON serializable
                if '_id' in mongo_series:
                    mongo_series.pop('_id', None)
                print(f"Found series directly in MongoDB: {mongo_series.get('name', 'Unknown')}")
                complete_series = mongo_series
                
                # Process genres properly
                if 'genre_names' not in complete_series or not complete_series['genre_names']:
                    # Try to extract genres from other fields
                    if 'genres' in complete_series and complete_series['genres']:
                        genres = complete_series['genres']
                        extracted_genres = []
                        
                        if isinstance(genres, list):
                            for genre in genres:
                                if isinstance(genre, dict) and 'name' in genre:
                                    extracted_genres.append(genre['name'])
                                elif isinstance(genre, str):
                                    extracted_genres.append(genre)
                        
                        complete_series['genre_names'] = extracted_genres
                        print(f"Extracted genres: {extracted_genres}")
            else:
                print(f"Series not found in MongoDB, falling back to model dataframe")
        except Exception as e:
            print(f"Error fetching series from MongoDB: {e}")
    
    # If we couldn't get the series from MongoDB, fall back to the model dataframe
    if complete_series is None:
        series_df = series_model['series_df']
        
        # First try exact match (highest priority)
        series = None
        
        # Try string format
        try:
            series_id_str = str(series_id)
            result = series_df[series_df['id'].astype(str) == series_id_str]
            if not result.empty:
                series = result.iloc[0].to_dict()
                print(f"Found series using string comparison: {series['name']}")
        except Exception as e:
            print(f"Error in string comparison: {e}")
        
        # Try integer format
        if series is None and isinstance(series_id, str) and series_id.isdigit():
            try:
                series_id_int = int(series_id)
                result = series_df[series_df['id'] == series_id_int]
                if not result.empty:
                    series = result.iloc[0].to_dict()
                    print(f"Found series using integer comparison: {series['name']}")
            except Exception as e:
                print(f"Error in integer comparison: {e}")
        
        # Last resort: check all rows
        if series is None:
            print("Trying manual search...")
            for i, row in series_df.iterrows():
                # Limit debug output
                if i % 1000 == 0:
                    print(f"Checking row {i}...")
                    
                if str(row['id']) == str(series_id):
                    series = row.to_dict()
                    print(f"Found series through manual search: {series['name']}")
                    break
        
        # If series still not found
        if series is None:
            print(f"Series with ID {series_id} not found after all attempts")
            print(f"Sample IDs in dataset: {series_df['id'].head(10).tolist()}")
            print(f"ID types in dataset: {series_df['id'].apply(type).unique()}")
            return render_template('404.html'), 404
        
        # Try to get enhanced data from MongoDB
        enhanced_series = None
        if db_instance:
            try:
                print(f"Looking for enhanced data in MongoDB for series ID: {series['id']}")
                enhanced_series = db_instance.get_detailed_series(series['id'])
                if enhanced_series:
                    # MongoDB returns ObjectId which is not JSON serializable
                    if '_id' in enhanced_series:
                        enhanced_series.pop('_id', None)
                    print(f"Found enhanced data in MongoDB for {series['name']}")
                else:
                    print(f"No enhanced data found in MongoDB for {series['name']}")
            except Exception as e:
                print(f"Error fetching series from MongoDB: {e}")
        
        # Merge model data with MongoDB data if available
        if enhanced_series:
            # Start with enhanced data as the base
            complete_series = enhanced_series
            # Ensure the core fields from the model are preserved
            complete_series['name'] = series['name']
            complete_series['id'] = series['id']
            
            # Make sure to get genres from model data if not in MongoDB
            if ('genre_names' not in complete_series or not complete_series['genre_names']) and 'genre_names' in series:
                complete_series['genre_names'] = series['genre_names']
                
            # Process genres if still missing
            if 'genre_names' not in complete_series or not complete_series['genre_names']:
                if 'genres' in complete_series and complete_series['genres']:
                    genres = complete_series['genres']
                    extracted_genres = []
                    
                    if isinstance(genres, list):
                        for genre in genres:
                            if isinstance(genre, dict) and 'name' in genre:
                                extracted_genres.append(genre['name'])
                            elif isinstance(genre, str):
                                extracted_genres.append(genre)
                    
                    complete_series['genre_names'] = extracted_genres
                    print(f"Extracted genres: {extracted_genres}")
        else:
            complete_series = series
    
    # Ensure we have an ID for recommendations
    series_id_for_recs = complete_series.get('id', series_id)
    series_name = complete_series.get('name', 'Unknown')
    
    # Add missing fields with default values to ensure template rendering works
    required_fields = {
        'genre_names': [],
        'vote_average': 0.0,
        'popularity': 0.0,
        'poster_path': None,
        'overview': '',
        'first_air_date': '',
        'last_air_date': '',
        'vote_count': 0,
        'number_of_seasons': 0,
        'number_of_episodes': 0,
        'episode_run_time': 0,
        'backdrop_path': None,
        'original_language': '',
        'networks': [],
        'status': 'Unknown',
        'type': ''
    }
    
    # Check if fields exist and add default values for missing ones
    for field, default_value in required_fields.items():
        if field not in complete_series or complete_series[field] is None:
            print(f"Adding missing field '{field}' with default value")
            complete_series[field] = default_value
    
    # Ensure genre_names is a list and not None
    if complete_series['genre_names'] is None:
        complete_series['genre_names'] = []
        
    # Debug genre names
    print(f"Final genre_names: {complete_series.get('genre_names', [])}")
    
    # Get recommendations
    try:
        print(f"Using name-based recommendation for series: {series_name}")
        recommendations = get_series_recommendations(series_name, series_model, top_n=9)
        
        # Enhance recommendations with MongoDB data if available
        if db_instance:
            enhanced_recommendations = []
            for rec in recommendations:
                try:
                    # Look for enhanced data
                    enhanced_rec = db_instance.get_detailed_series(rec['id'])
                    if enhanced_rec:
                        # MongoDB returns ObjectId which is not JSON serializable
                        if '_id' in enhanced_rec:
                            enhanced_rec.pop('_id', None)
                        # Merge model recommendation with enhanced data
                        merged_rec = {**rec, **enhanced_rec}
                        # Ensure core fields are preserved
                        merged_rec['title'] = rec['title']
                        merged_rec['id'] = rec['id']
                        merged_rec['similarity'] = rec['similarity']
                        
                        # Process genres for recommendations too
                        if 'genre_names' not in merged_rec or not merged_rec['genre_names']:
                            if 'genres' in merged_rec and merged_rec['genres']:
                                genres = merged_rec['genres']
                                extracted_genres = []
                                
                                if isinstance(genres, list):
                                    for genre in genres:
                                        if isinstance(genre, dict) and 'name' in genre:
                                            extracted_genres.append(genre['name'])
                                        elif isinstance(genre, str):
                                            extracted_genres.append(genre)
                                
                                merged_rec['genre_names'] = extracted_genres
                        
                        enhanced_recommendations.append(merged_rec)
                    else:
                        enhanced_recommendations.append(rec)
                except Exception as e:
                    print(f"Error enhancing recommendation: {e}")
                    enhanced_recommendations.append(rec)
            
            # Replace recommendations with enhanced ones
            if enhanced_recommendations:
                recommendations = enhanced_recommendations
        
        # Ensure each recommendation has all required fields
        for rec in recommendations:
            for field, default_value in required_fields.items():
                if field not in rec or rec[field] is None:
                    rec[field] = default_value
                    
        print(f"Generated {len(recommendations)} recommendations")
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        recommendations = []
    
    return render_template('series_recommender.html', series=complete_series, recommendations=recommendations)

@recommender_bp.route('/api/movie-recommendations/<movie_id>')
def api_movie_recommendations(movie_id):
    if not movie_model:
        load_models()
        if not movie_model:
            return jsonify({'error': 'Movie recommendation model not loaded'}), 500
    
    # Find the movie in the DataFrame
    movies_df = movie_model['movies_df']
    
    # Try different formats for ID matching
    movie = None
    
    # Try as string
    result = movies_df[movies_df['id'].astype(str) == str(movie_id)]
    if not result.empty:
        movie = result.iloc[0]
    
    # Try as integer if not found
    if movie is None and isinstance(movie_id, str) and movie_id.isdigit():
        result = movies_df[movies_df['id'] == int(movie_id)]
        if not result.empty:
            movie = result.iloc[0]
    
    if movie is None:
        return jsonify({'error': 'Movie not found'}), 404
    
    # Get recommendations
    try:
        recommendations = get_movie_recommendations(movie['title'], movie_model, top_n=9)
        
        # Enhance recommendations with MongoDB data if available
        if db_instance:
            for rec in recommendations:
                try:
                    enhanced_rec = db_instance.get_detailed_movie(rec['id'])
                    if enhanced_rec:
                        # Remove MongoDB ObjectId
                        if '_id' in enhanced_rec:
                            enhanced_rec.pop('_id', None)
                        # Update recommendation with extra data
                        for key, value in enhanced_rec.items():
                            if key not in rec or rec[key] is None:
                                rec[key] = value
                except Exception as e:
                    print(f"Error enhancing recommendation in API: {e}")
        
        return jsonify({'recommendations': recommendations})
    except Exception as e:
        return jsonify({'error': f'Error getting recommendations: {str(e)}'}), 500

@recommender_bp.route('/api/series-recommendations/<series_id>')
def api_series_recommendations(series_id):
    if not series_model:
        load_models()
        if not series_model:
            return jsonify({'error': 'Series recommendation model not loaded'}), 500
    
    # Find the series in the DataFrame
    series_df = series_model['series_df']
    
    # Try different formats for ID matching
    series = None
    
    # Try as string
    result = series_df[series_df['id'].astype(str) == str(series_id)]
    if not result.empty:
        series = result.iloc[0]
    
    # Try as integer if not found
    if series is None and isinstance(series_id, str) and series_id.isdigit():
        result = series_df[series_df['id'] == int(series_id)]
        if not result.empty:
            series = result.iloc[0]
    
    if series is None:
        return jsonify({'error': 'Series not found'}), 404
    
    # Get recommendations
    try:
        recommendations = get_series_recommendations(series['name'], series_model, top_n=9)
        
        # Enhance recommendations with MongoDB data if available
        if db_instance:
            for rec in recommendations:
                try:
                    enhanced_rec = db_instance.get_detailed_series(rec['id'])
                    if enhanced_rec:
                        # Remove MongoDB ObjectId
                        if '_id' in enhanced_rec:
                            enhanced_rec.pop('_id', None)
                        # Update recommendation with extra data
                        for key, value in enhanced_rec.items():
                            if key not in rec or rec[key] is None:
                                rec[key] = value
                except Exception as e:
                    print(f"Error enhancing recommendation in API: {e}")
        
        return jsonify({'recommendations': recommendations})
    except Exception as e:
        return jsonify({'error': f'Error getting recommendations: {str(e)}'}), 500
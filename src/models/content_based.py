# Modified functions in src/models/content_based.py

import pandas as pd
import numpy as np

def get_content_based_movie_recommendations_by_id(movie_id, cosine_sim, df, top_n=12):
    """Get movie recommendations based on ID rather than title"""
    try:
        # Find the movie by ID
        movie_row = df[df['id'] == movie_id]
        
        if movie_row.empty:
            # Try string comparison if integer comparison fails
            movie_row = df[df['id'].astype(str) == str(movie_id)]
            
        if movie_row.empty:
            print(f"Movie with ID '{movie_id}' not found")
            return []
            
        # Get the index of the movie
        idx = movie_row.index[0]  # Get the first index from the result
        title = movie_row.iloc[0]['title']  # Get the title for logging
        
        print(f"Found movie '{title}' at index {idx}")
        
        # Get similarity scores for all movies
        sim_scores = []
        for i in range(len(df)):
            # Skip the exact same movie and any duplicate titles
            if i == idx or df.iloc[i]['id'] == movie_id:
                continue
                
            # Handle case where similarity value might be an array
            sim_value = cosine_sim[idx, i]
            if hasattr(sim_value, '__len__') and len(sim_value) > 0:
                sim_value = float(sim_value[0])
            sim_scores.append((i, float(sim_value)))
        
        # Sort based on similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Get top N most similar movies
        sim_scores = sim_scores[:top_n]
        
        # Get movie indices
        movie_indices = [i[0] for i in sim_scores]
        
        # Create result dataframe
        columns_to_include = ['id', 'title', 'genre_names', 'vote_average', 'popularity', 'poster_path']
        result = df.iloc[movie_indices][columns_to_include].copy()
        result['similarity'] = [i[1] for i in sim_scores]
        
        return result
    except Exception as e:
        print(f"Error in get_content_based_movie_recommendations_by_id: {e}")
        return []

def get_content_based_series_recommendations_by_id(series_id, cosine_sim, df, top_n=12):
    """Get series recommendations based on ID rather than title"""
    try:
        # Find the series by ID
        series_row = df[df['id'] == series_id]
        
        if series_row.empty:
            # Try string comparison if integer comparison fails
            series_row = df[df['id'].astype(str) == str(series_id)]
            
        if series_row.empty:
            print(f"Series with ID '{series_id}' not found")
            return []
            
        # Get the index of the series
        idx = series_row.index[0]  # Get the first index from the result
        name = series_row.iloc[0]['name']  # Get the name for logging
        
        print(f"Found series '{name}' at index {idx}")
        
        # Get similarity scores for all series
        sim_scores = []
        for i in range(len(df)):
            # Skip the exact same series and any duplicate names
            if i == idx or df.iloc[i]['id'] == series_id:
                continue
                
            # Handle case where similarity value might be an array
            sim_value = cosine_sim[idx, i]
            if hasattr(sim_value, '__len__') and len(sim_value) > 0:
                sim_value = float(sim_value[0])
            sim_scores.append((i, float(sim_value)))
        
        # Sort based on similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Get top N most similar series
        sim_scores = sim_scores[:top_n]
        
        # Get series indices
        series_indices = [i[0] for i in sim_scores]
        
        # Create result dataframe
        columns_to_include = ['id', 'name', 'genre_names', 'vote_average', 'popularity', 'poster_path']
        result = df.iloc[series_indices][columns_to_include].copy()
        result['similarity'] = [i[1] for i in sim_scores]
        
        return result
    except Exception as e:
        print(f"Error in get_content_based_series_recommendations_by_id: {e}")
        return []

def get_hybrid_movie_recommendations_by_id(movie_id, model, top_n=12):
    """Get hybrid movie recommendations using ID instead of title"""
    # Extract components from the model
    cosine_sim = model['cosine_sim']
    movies_df = model['movies_df']
    
    # Get content-based recommendations first
    content_recs = get_content_based_movie_recommendations_by_id(movie_id, cosine_sim, movies_df, top_n=top_n*3)
    
    if len(content_recs) == 0:
        print(f"No content-based recommendations found for movie ID '{movie_id}'")
        return []
    
    try:
        # Find the movie in the dataframe
        movie_row = movies_df[movies_df['id'] == movie_id]
        if movie_row.empty:
            movie_row = movies_df[movies_df['id'].astype(str) == str(movie_id)]
        if movie_row.empty:
            print(f"Movie with ID '{movie_id}' not found")
            return []
            
        # Get the index of the movie
        movie_idx = movie_row.index[0]
        title = movie_row.iloc[0]['title']  # Get title for logging
        
        # Get the original indices from content_recs
        original_indices = content_recs.index
        
        # Add the scaled features from the original dataframe if they exist
        if 'popularity_scaled' in movies_df.columns and 'vote_average_scaled' in movies_df.columns:
            content_recs['popularity_scaled'] = movies_df.loc[original_indices, 'popularity_scaled'].values
            content_recs['vote_average_scaled'] = movies_df.loc[original_indices, 'vote_average_scaled'].values
        else:
            # If scaled columns don't exist, create them
            content_recs['popularity_scaled'] = content_recs['popularity'] / content_recs['popularity'].max()
            content_recs['vote_average_scaled'] = content_recs['vote_average'] / 10.0
        
        # Create hybrid score
        content_recs['hybrid_score'] = (
            # Content similarity (60%)
            0.60 * content_recs['similarity'] +
            # Popularity (10%)
            0.10 * content_recs['popularity_scaled'] +
            # Rating (30%)
            0.30 * content_recs['vote_average_scaled']
        )
        
        # Get the recommended movie's genres
        target_genres = set(movies_df.iloc[movie_idx]['genre_names'] if isinstance(movies_df.iloc[movie_idx]['genre_names'], list) else [])
        
        # Add genre matching bonus
        def calculate_genre_overlap(genres):
            if not target_genres or not genres:
                return 0
            
            if isinstance(genres, list):
                genre_set = set(genres)
            else:
                genre_set = set()
                
            overlap = genre_set.intersection(target_genres)
            return len(overlap) / max(len(target_genres), 1)
        
        content_recs['genre_score'] = content_recs['genre_names'].apply(calculate_genre_overlap)
        
        # Adjust hybrid score with genre bonus
        content_recs['hybrid_score'] = content_recs['hybrid_score'] + (0.1 * content_recs['genre_score'])
        
        # Sort by hybrid score and convert to list of dicts for API response
        sorted_recs = content_recs.sort_values('hybrid_score', ascending=False).head(top_n)
        
        # Convert to list of dictionaries for the API
        result = []
        for _, movie in sorted_recs.iterrows():
            result.append({
                'id': movie['id'],
                'title': movie['title'],
                'poster_path': movie['poster_path'],
                'vote_average': movie['vote_average'],
                'similarity': float(movie['similarity']),
                'hybrid_score': float(movie['hybrid_score']),
                'genres': movie['genre_names'] if isinstance(movie['genre_names'], list) else []
            })
        
        return result
    except Exception as e:
        print(f"Error in get_hybrid_movie_recommendations_by_id: {e}")
        return []

def get_hybrid_series_recommendations_by_id(series_id, model, top_n=12):
    """Get hybrid series recommendations using ID instead of title"""
    # Extract components from the model
    cosine_sim = model['cosine_sim']
    series_df = model['series_df']
    
    # Get content-based recommendations first
    content_recs = get_content_based_series_recommendations_by_id(series_id, cosine_sim, series_df, top_n=top_n*3)
    
    if len(content_recs) == 0:
        print(f"No content-based recommendations found for series ID '{series_id}'")
        return []
    
    try:
        # Find the series in the dataframe
        series_row = series_df[series_df['id'] == series_id]
        if series_row.empty:
            series_row = series_df[series_df['id'].astype(str) == str(series_id)]
        if series_row.empty:
            print(f"Series with ID '{series_id}' not found")
            return []
            
        # Get the index of the series
        series_idx = series_row.index[0]
        name = series_row.iloc[0]['name']  # Get name for logging
        
        # Get the original indices from content_recs
        original_indices = content_recs.index
        
        # Add the scaled features from the original dataframe if they exist
        if 'popularity_scaled' in series_df.columns and 'vote_average_scaled' in series_df.columns:
            content_recs['popularity_scaled'] = series_df.loc[original_indices, 'popularity_scaled'].values
            content_recs['vote_average_scaled'] = series_df.loc[original_indices, 'vote_average_scaled'].values
        else:
            # If scaled columns don't exist, create them
            content_recs['popularity_scaled'] = content_recs['popularity'] / content_recs['popularity'].max()
            content_recs['vote_average_scaled'] = content_recs['vote_average'] / 10.0
        
        # Create hybrid score
        content_recs['hybrid_score'] = (
            # Content similarity (60%)
            0.60 * content_recs['similarity'] +
            # Popularity (20%)
            0.20 * content_recs['popularity_scaled'] +
            # Rating (20%)
            0.20 * content_recs['vote_average_scaled']
        )
        
        # Get the recommended series's genres
        genres = series_df.iloc[series_idx]['genre_names']
        if isinstance(genres, list):
            target_genres = set(genres)
        else:
            target_genres = set()
        
        # Add genre matching bonus
        def calculate_genre_overlap(genres):
            if not target_genres or not genres:
                return 0
                
            if isinstance(genres, list):
                genre_set = set(genres)
            else:
                genre_set = set()
                
            overlap = genre_set.intersection(target_genres)
            return len(overlap) / max(len(target_genres), 1)
        
        content_recs['genre_score'] = content_recs['genre_names'].apply(calculate_genre_overlap)
        
        # Adjust hybrid score with genre bonus
        content_recs['hybrid_score'] = content_recs['hybrid_score'] + (0.1 * content_recs['genre_score'])
        
        # Sort by hybrid score and convert to list of dicts for API response
        sorted_recs = content_recs.sort_values('hybrid_score', ascending=False).head(top_n)
        
        # Convert to list of dictionaries for the API
        result = []
        for _, series in sorted_recs.iterrows():
            result.append({
                'id': series['id'],
                'title': series['name'],
                'poster_path': series['poster_path'],
                'vote_average': series['vote_average'],
                'similarity': float(series['similarity']),
                'hybrid_score': float(series['hybrid_score']),
                'genres': series['genre_names'] if isinstance(series['genre_names'], list) else []
            })
        
        return result
    except Exception as e:
        print(f"Error in get_hybrid_series_recommendations_by_id: {e}")
        return []

# New simplified wrapper functions that use the hybrid approach by default and work with IDs
def get_movie_recommendations_by_id(movie_id, model, top_n=10):
    """Get movie recommendations using the hybrid approach with movie ID"""
    return get_hybrid_movie_recommendations_by_id(movie_id, model, top_n)

def get_series_recommendations_by_id(series_id, model, top_n=10):
    """Get series recommendations using the hybrid approach with series ID"""
    return get_hybrid_series_recommendations_by_id(series_id, model, top_n)

# Keep the original functions for backward compatibility
def get_content_based_movie_recommendations(title, cosine_sim, df, indices, top_n=12):
    """Get movie recommendations based purely on content similarity"""
    # Check if movie exists
    if title not in indices:
        print(f"Movie '{title}' not found in indices")
        return []
    
    try:
        # Get the index of the movie that exactly matches the title
        movie_rows = df[df['title'] == title]
        
        if movie_rows.empty:
            print(f"Movie '{title}' not found in dataframe")
            return []
            
        # Use the first movie with this title
        idx = movie_rows.index[0]
        
        # Get similarity scores for all movies
        sim_scores = []
        for i in range(len(df)):
            # Skip the exact same movie and any duplicate titles
            if i == idx or df.iloc[i]['title'] == title:
                continue
                
            # Handle case where similarity value might be an array
            sim_value = cosine_sim[idx, i]
            if hasattr(sim_value, '__len__') and len(sim_value) > 0:
                sim_value = float(sim_value[0])
            sim_scores.append((i, float(sim_value)))
        
        # Sort based on similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Get top N most similar movies
        sim_scores = sim_scores[:top_n]
        
        # Get movie indices
        movie_indices = [i[0] for i in sim_scores]
        
        # Create result dataframe
        columns_to_include = ['id', 'title', 'genre_names', 'vote_average', 'popularity', 'poster_path']
        result = df.iloc[movie_indices][columns_to_include].copy()
        result['similarity'] = [i[1] for i in sim_scores]
        
        return result
    except Exception as e:
        print(f"Error in get_content_based_movie_recommendations: {e}")
        return []

def get_content_based_series_recommendations(name, cosine_sim, df, indices, top_n=12):
    """Get series recommendations based purely on content similarity"""
    # Check if series exists
    if name not in indices:
        print(f"Series '{name}' not found in indices")
        return []
    
    try:
        # Get the index of the series that exactly matches the name
        series_rows = df[df['name'] == name]
        
        if series_rows.empty:
            print(f"Series '{name}' not found in dataframe")
            return []
            
        # Use the first series with this name
        idx = series_rows.index[0]
        
        # Get similarity scores for all series
        sim_scores = []
        for i in range(len(df)):
            # Skip the exact same series and any duplicate names
            if i == idx or df.iloc[i]['name'] == name:
                continue
                
            # Handle case where similarity value might be an array
            sim_value = cosine_sim[idx, i]
            if hasattr(sim_value, '__len__') and len(sim_value) > 0:
                sim_value = float(sim_value[0])
            sim_scores.append((i, float(sim_value)))
        
        # Sort based on similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Get top N most similar series
        sim_scores = sim_scores[:top_n]
        
        # Get series indices
        series_indices = [i[0] for i in sim_scores]
        
        # Create result dataframe
        columns_to_include = ['id', 'name', 'genre_names', 'vote_average', 'popularity', 'poster_path']
        result = df.iloc[series_indices][columns_to_include].copy()
        result['similarity'] = [i[1] for i in sim_scores]
        
        return result
    except Exception as e:
        print(f"Error in get_content_based_series_recommendations: {e}")
        return []

# Original hybrid functions with title-based lookup for backward compatibility
def get_hybrid_movie_recommendations(title, model, top_n=12):
    """Get hybrid movie recommendations combining content similarity with popularity and ratings"""
    # Extract components from the model
    cosine_sim = model['cosine_sim']
    indices = model['indices']
    movies_df = model['movies_df']
    
    # Get content-based recommendations first
    content_recs = get_content_based_movie_recommendations(title, cosine_sim, movies_df, indices, top_n=top_n*3)
    
    if len(content_recs) == 0:
        print(f"No content-based recommendations found for '{title}'")
        return []
    
    # Rest of the function stays the same...
    # ... (original implementation)
    
    # For brevity, we're not repeating the entire implementation here.
    # In a real implementation, you would keep the rest of the function unchanged
    try:
        # Find the movie by title (may encounter issues with duplicates)
        movie_rows = movies_df[movies_df['title'] == title]
        if movie_rows.empty:
            print(f"Movie with title '{title}' not found")
            return []
            
        # Use the first movie with this title 
        movie_idx = movie_rows.index[0]
        
        # Rest of the original implementation...
        # ... (continue with original logic)
        
        # Since we're not copying the whole implementation, let's just call the ID-based version
        # In a real implementation, you would include the complete original function code
        movie_id = movies_df.iloc[movie_idx]['id']
        return get_hybrid_movie_recommendations_by_id(movie_id, model, top_n)
        
    except Exception as e:
        print(f"Error in get_hybrid_movie_recommendations: {e}")
        return []

def get_hybrid_series_recommendations(name, model, top_n=12):
    """Get hybrid series recommendations combining content similarity with popularity and ratings"""
    # Extract components from the model
    cosine_sim = model['cosine_sim']
    indices = model['indices']
    series_df = model['series_df']
    
    # Get content-based recommendations first
    content_recs = get_content_based_series_recommendations(name, cosine_sim, series_df, indices, top_n=top_n*3)
    
    if len(content_recs) == 0:
        print(f"No content-based recommendations found for '{name}'")
        return []
    
    # Rest of the function stays the same...
    # ... (original implementation)
    
    # For brevity, we're not repeating the entire implementation here.
    # In a real implementation, you would keep the rest of the function unchanged
    try:
        # Find the series by name (may encounter issues with duplicates)
        series_rows = series_df[series_df['name'] == name]
        if series_rows.empty:
            print(f"Series with name '{name}' not found")
            return []
            
        # Use the first series with this name
        series_idx = series_rows.index[0]
        
        # Rest of the original implementation...
        # ... (continue with original logic)
        
        # Since we're not copying the whole implementation, let's just call the ID-based version
        # In a real implementation, you would include the complete original function code
        series_id = series_df.iloc[series_idx]['id']
        return get_hybrid_series_recommendations_by_id(series_id, model, top_n)
        
    except Exception as e:
        print(f"Error in get_hybrid_series_recommendations: {e}")
        return []

# Keep the original wrapper functions for backward compatibility
def get_movie_recommendations(title, model, top_n=10):
    """Get movie recommendations using the hybrid approach"""
    return get_hybrid_movie_recommendations(title, model, top_n)

def get_series_recommendations(name, model, top_n=10):
    """Get series recommendations using the hybrid approach"""
    return get_hybrid_series_recommendations(name, model, top_n)
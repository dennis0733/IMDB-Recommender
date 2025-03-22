# data_collector.py
import requests
import json
import time
import os
from tqdm import tqdm
from dotenv import load_dotenv



def collect_tmdb_data():
    # Create data directory
    os.makedirs('raw_data', exist_ok=True)
    
    load_dotenv(dotenv_path='.env')
    # Your TMDb API key
    api_key = os.getenv('TMDB_API_KEY')

    # Collect movie data
    print("Collecting movie data...")
    all_movies = []
    
    # Get total number of pages (TMDb has a max of 500 pages)
    total_pages = 500
    try:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&page=1"
        response = requests.get(url)
        data = response.json()
        total_pages = min(500, data.get('total_pages', 500))
    except Exception as e:
        print(f"Error getting total pages: {e}")
    
    # Collect all pages
    for page in tqdm(range(1, total_pages + 1)):
        try:
            url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&page={page}"
            response = requests.get(url)
            data = response.json()
            all_movies.extend(data.get('results', []))
            time.sleep(0.25)  # Avoid rate limiting
        except Exception as e:
            print(f"Error on page {page}: {e}")
    
    # Save movie data
    with open('raw_data/movies.json', 'w', encoding='utf-8') as f:
        json.dump(all_movies, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(all_movies)} movies to data/movies.json")
    
    
    # Collect TV series data
    print("\nCollecting TV series data...")
    all_series = []
    
    # Get total number of pages for TV series
    total_pages = 500
    try:
        url = f"https://api.themoviedb.org/3/tv/popular?api_key={api_key}&page=1"
        response = requests.get(url)
        data = response.json()
        total_pages = min(500, data.get('total_pages', 500))
    except Exception as e:
        print(f"Error getting total pages: {e}")
    
    # Collect all pages
    for page in tqdm(range(1, total_pages + 1)):
        try:
            url = f"https://api.themoviedb.org/3/tv/popular?api_key={api_key}&page={page}"
            response = requests.get(url)
            data = response.json()
            all_series.extend(data.get('results', []))
            time.sleep(0.25)  # Avoid rate limiting
        except Exception as e:
            print(f"Error on page {page}: {e}")
    
    # Save TV series data
    with open('raw_data/tv_series.json', 'w', encoding='utf-8') as f:
        json.dump(all_series, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(all_series)} TV series to data/tv_series.json")
    
    # Collect genre data for both movies and TV
    print("\nCollecting genre data...")
    
    # Movie genres
    try:
        url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={api_key}"
        response = requests.get(url)
        movie_genres = response.json()
        with open('raw_data/movie_genres.json', 'w', encoding='utf-8') as f:
            json.dump(movie_genres, f, ensure_ascii=False, indent=4)
        print(f"Saved movie genres to data/movie_genres.json")
    except Exception as e:
        print(f"Error collecting movie genres: {e}")
    
    # TV genres
    try:
        url = f"https://api.themoviedb.org/3/genre/tv/list?api_key={api_key}"
        response = requests.get(url)
        tv_genres = response.json()
        with open('raw_data/tv_genres.json', 'w', encoding='utf-8') as f:
            json.dump(tv_genres, f, ensure_ascii=False, indent=4)
        print(f"Saved TV genres to data/tv_genres.json")
    except Exception as e:
        print(f"Error collecting TV genres: {e}")


        # Get detailed information movies and series
    print("\nCollecting detailed information for top movies...")
    detailed_movies = []
    for movie in tqdm(all_movies):  # Get details 
        try:
            movie_id = movie['id']
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&append_to_response=credits,keywords,similar,videos"
            response = requests.get(url)
            detailed_info = response.json()
            detailed_movies.append(detailed_info)
            time.sleep(0.25)  # Avoid rate limiting
        except Exception as e:
            print(f"Error getting details for movie {movie.get('title', movie_id)}: {e}")
    
    # Save detailed movie data
    with open('raw_data/detailed_movies.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_movies, f, ensure_ascii=False, indent=4)
    print(f"Saved detailed info for {len(detailed_movies)} movies to data/detailed_movies.json")
    
    
    print("\nCollecting detailed information for top TV series...")
    detailed_series = []
    for series in tqdm(all_series):  # Get details
        try:
            series_id = series['id']
            url = f"https://api.themoviedb.org/3/tv/{series_id}?api_key={api_key}&append_to_response=credits,keywords,similar,videos"
            response = requests.get(url)
            detailed_info = response.json()
            detailed_series.append(detailed_info)
            time.sleep(0.25)  # Avoid rate limiting
        except Exception as e:
            print(f"Error getting details for series {series.get('name', series_id)}: {e}")
    
    # Save detailed TV series data
    with open('raw_data/detailed_series.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_series, f, ensure_ascii=False, indent=4)
    print(f"Saved detailed info for {len(detailed_series)} series to data/detailed_series.json")
    
    print("\nData collection complete!")

if __name__ == "__main__":
    collect_tmdb_data()
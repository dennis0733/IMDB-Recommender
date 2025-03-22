import os
import requests
import time
import re

DATA_DIR = "data/processed"
os.makedirs(DATA_DIR, exist_ok=True)

# Function to convert Google Drive sharing URL to direct download URL
def get_direct_link(sharing_url):
    # Extract the file ID from the sharing URL
    file_id_match = re.search(r"/d/([a-zA-Z0-9_-]+)", sharing_url)
    if file_id_match:
        file_id = file_id_match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return sharing_url

# Mapping of filenames to Google Drive sharing URLs
FILES = {
    "imdb_recommender.detailed_movies.json": "https://drive.google.com/file/d/1SYLWiKmucfRIDazEp-XaCEXSHlkby2t9/view?usp=drive_link",
    "imdb_recommender.detailed_series.json": "https://drive.google.com/file/d/1VbM3ca-w5CM-ac-jFiuY2Ngxvm2dnMh1/view?usp=drive_link",
    "imdb_recommender.movie_genres.json": "https://drive.google.com/file/d/1AuAlj_2RbcE8KLn-lxcWLUR71dS09u_a/view?usp=drive_link",
    "imdb_recommender.tv_genres.json": "https://drive.google.com/file/d/1f37l8cclBhjQ-HNc_pTCSxBksSHTtmAm/view?usp=drive_link",
    "imdb_recommender.movies.json": "https://drive.google.com/file/d/1kJ2flln6uU5xHWDjGS7QW_OJtdw1-iJM/view?usp=drive_link",
    "imdb_recommender.series.json": "https://drive.google.com/file/d/1UDvoGtwnXE0-Fr7tEuqGS76gkH0_9EdX/view?usp=drive_link"
}

# Download the files
for filename, sharing_url in FILES.items():
    file_path = os.path.join(DATA_DIR, filename)
    
    # Skip if file already exists and has content
    if os.path.exists(file_path) and os.path.getsize(file_path) > 100:
        print(f"{filename} already exists, skipping download")
        continue
        
    print(f"Downloading {filename}...")
    start_time = time.time()
    
    # Get direct download URL
    download_url = get_direct_link(sharing_url)
    
    # For large files, we need to handle the Google Drive download warning
    session = requests.Session()
    
    # First request to get cookies and confirmation token
    response = session.get(download_url, stream=True)
    
    # Check if we need to bypass the warning screen
    if "confirm" in response.text:
        confirm_match = re.search(r"confirm=([0-9A-Za-z_-]+)", response.text)
        if confirm_match:
            confirm_token = confirm_match.group(1)
            download_url = f"{download_url}&confirm={confirm_token}"
            response = session.get(download_url, stream=True)
    
    # Download the file
    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
    end_time = time.time()
    print(f"Downloaded {filename} in {end_time - start_time:.2f} seconds")

print("All data files downloaded successfully!")
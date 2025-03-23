# IMDB Movie and Series Recommender

![IMDB Recommender](https://github.com/dennis0733/imdb-recommender/raw/main/web/static/images/imdb-logo.png)

## 🎬 Overview

IMDB Movie and Series Recommender is an advanced content-based recommendation system that helps users discover movies and TV shows tailored to their preferences. Built with data from The Movie Database (TMDb), this application leverages sophisticated machine learning techniques to provide personalized recommendations based on content similarity and user preferences.

Live demo: [https://imdb-recommender.up.railway.app](https://imdb-recommender.up.railway.app)

## ✨ Features

- **Personalized Recommendations**: Get movie and TV series recommendations based on your preferences
- **Advanced Search**: Find content by title, genre, cast, and more
- **Detailed Analytics**: Explore insights and trends from our extensive movie and TV series database
- **Responsive Design**: Enjoy a seamless experience across desktop and mobile devices
- **Content-Based Filtering**: Discover new content similar to what you already love
- **Hybrid Recommendation System**: Recommendations based on content similarity, popularity, and user ratings

## 🧠 Technical Details

### Recommendation Engine

The application implements a sophisticated content-based filtering approach with the following key components:

#### For Movies:
- **Feature Engineering**: Extracts and processes multiple content features including genres, keywords, cast, directors, and production companies
- **TF-IDF Vectorization**: Creates separate TF-IDF vectors for each feature with custom weights:
  - Keywords (10.0)
  - Title (2.5)
  - Cast (2.5)
  - Genre (2.0)
  - Directors (1.5)
  - Overview (1.0)
  - Production companies (0.5)
- **Similarity Calculation**: Computes cosine similarity between content items
- **Hybrid Scoring**: Combines content similarity (60%), user ratings (30%), and popularity (10%)

#### For TV Series:
- **Feature Engineering**: Similar to movies, but with additional TV-specific features like creators, networks, and status
- **TF-IDF Vectorization**: Custom weights for feature importance:
  - Keywords (9.0)
  - Genre (4.0)
  - Title/Name (2.5)
  - Cast (2.5)
  - Creators (2.0)
  - Overview (1.5)
  - Networks (1.5)
  - Production companies (0.5)
- **Similarity Calculation**: Cosine similarity for content matching
- **Hybrid Scoring**: Balances content similarity with popularity and ratings, plus a genre matching bonus

### Data Analysis

The application includes comprehensive data analysis dashboards for both movies and TV series, displaying:

- Genre distribution
- Rating patterns
- Release trends over time
- Language distribution
- Runtime statistics
- Budget vs. revenue analysis (for movies)
- Production company analysis
- Seasons and episodes statistics (for series)
- Network analysis (for series)

## 🛠️ Technology Stack

- **Backend**: Python, Flask
- **Database**: MongoDB Atlas
- **Data Processing**: Pandas, NumPy, SciPy
- **Machine Learning**: Scikit-learn
- **Visualization**: Matplotlib, Plotly
- **Deployment**: Railway

## 📊 Data Sources

- **The Movie Database (TMDb)**: Primary data source for movie and TV series information
- **MongoDB Atlas**: Cloud database for storing processed data and models

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- MongoDB
- Virtual environment (recommended)

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/imdb-recommender.git
cd imdb-recommender
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables (create a .env file inside data folder)
```
MONGODB_URI=your_mongodb_connection_string
TMDB_API_KEY=your_tmdb_api_key
```

5. Collect data from TMDb API (this may take some time)
```bash
python data_collector.py
```

6. Import the collected data to MongoDB
```bash
python mongodb_import.py
```

7. Run the application
```bash
python app.py
```

8. Open your browser and navigate to `http://localhost:5000`

## 📈 Data Processing Pipeline

1. **Data Collection**: 
   - Fetch movie and TV series data from TMDb API using `data_collector.py`
   - Collect basic and detailed information including credits, keywords, and similar content
   - Store raw data as JSON files in the `raw_data` directory

2. **Data Import**:
   - Import collected data to MongoDB Atlas using `mongodb_import.py`
   - Remove duplicate entries during the import process
   - Structure data into separate collections for movies, series, and genres

3. **Data Cleaning & Preprocessing**:
   - Process raw data and handle missing values
   - Convert genre IDs to human-readable names
   - Extract relevant features for recommendation models

4. **Feature Engineering**:
   - Extract text features from various content attributes
   - Apply TF-IDF vectorization with custom weights
   - Normalize numerical features using MinMaxScaler

5. **Model Training**:
   - Build content-based recommender models for movies and TV series
   - Calculate similarity matrices using weighted features
   - Implement hybrid scoring systems that balance similarity with popularity and ratings

6. **Data Analysis**:
   - Generate statistical insights using Pandas and NumPy
   - Create visualizations with Matplotlib using `generate_plots.py`
   - Store analysis results as JSON for use in dashboards

7. **Model Deployment**:
   - Save trained models using Joblib for efficient loading
   - Deploy the Flask application with recommendation capabilities
   - Serve recommendations and visualizations through the web interface

## 📝 Project Structure

```
imdb-recommender/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── data_collector.py           # Script to collect data from TMDb API
├── mongodb_import.py           # Script to import data to MongoDB
└── local_analysis_generator.py           # Data visualization scripts
├── raw_data/                   # Raw JSON data collected from TMDb
│   ├── movies.json             # Basic movie data
│   ├── tv_series.json          # Basic TV series data
│   ├── movie_genres.json       # Movie genre mappings
│   ├── tv_genres.json          # TV genre mappings
│   ├── detailed_movies.json    # Detailed movie data with credits, keywords, etc.
│   └── detailed_series.json    # Detailed series data with credits, keywords, etc.
├── src/
│   ├── data/
│   │   ├── database.py         # MongoDB connection and operations
│   │   └── tmdb_api.py         # TMDb API client
│   ├── models/
│       ├── content_based.py    # Recommendation algorithms
│       └── utils.py            # Helper functions
│  
├── notebooks/
│   ├── movie_recommender.ipynb # Movie recommendation model development
│   ├── series_recommender.ipynb# Series recommendation model development
│   └── data_exploration.ipynb  # Data analysis and exploration
└── web/
    ├── routes/
    │   ├── recommender.py      # Recommendation route handlers
    │   └── analysis.py         # Analysis dashboard route handlers
    ├── static/
    │   ├── css/                # Stylesheets
    │   ├── js/                 # JavaScript files
    │   ├── images/             # Image assets
    │   ├── plots/              # Generated visualization plots
    │   │   ├── movies/         # Movie analysis visualizations
    │   │   └── series/         # TV series analysis visualizations
    │   └── data/               # JSON data for dashboards
    └── templates/              # HTML templates
```

## 📊 Analytics Dashboards

The application provides two comprehensive analytics dashboards:

1. **Movie Analysis Dashboard**: Explore trends and patterns in the movie database
   - Total movies analyzed: 9,464+
   - Average rating: 6.4
   - Most popular genre: Drama
   - Average runtime: 104 minutes

2. **TV Series Analysis Dashboard**: Discover insights about TV series
   - Total series analyzed: 8,596+
   - Average rating: 5.4
   - Most popular genre: Drama
   - Average seasons: 5.7

## 🔄 How Recommendations Work

1. When a user selects a movie or TV show, the system:
   - Retrieves the content's features from the database
   - Finds similar content using pre-computed similarity matrices
   - Applies a hybrid scoring system that balances similarity with popularity and ratings
   - Returns personalized recommendations sorted by relevance

2. The recommendation quality is enhanced by:
   - Feature weighting that prioritizes important content attributes
   - Minimum vote thresholds to ensure quality recommendations
   - Genre matching bonuses to maintain thematic relevance
   - Popularity factors to surface trending content

## 🔮 Future Improvements

- [ ] Add collaborative filtering to enhance recommendation quality
- [ ] Implement user accounts and personalized recommendation history
- [ ] Add more movies and TV series to the database
- [ ] Optimize recommender system performance
- [ ] Implement A/B testing for recommendation algorithms
- [ ] Add diversity measures to avoid recommendation echo chambers
- [ ] Real-time model updates as new content is released

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [The Movie Database (TMDb)](https://www.themoviedb.org/) for providing the API and data
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) for database hosting
- [Railway](https://railway.app/) for application deployment
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Scikit-learn](https://scikit-learn.org/) for machine learning components

---

Developed by [Şükrü Deniz Çilek]

[![GitHub stars](https://img.shields.io/github/stars/dennis0733/imdb-recommender?style=social)](https://github.com/dennis0733/imdb-recommender)

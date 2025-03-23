# generate_plots.py
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import sys
from scipy import stats
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Create output directories
os.makedirs('web/static/plots/movies', exist_ok=True)
os.makedirs('web/static/plots/series', exist_ok=True)
os.makedirs('web/static/data', exist_ok=True)

# Function to save plot
def save_plot(fig, filename):
    fig.savefig(filename, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved plot: {filename}")

# Import Database 
from src.data.database import Database

print("Connecting to MongoDB...")
db = Database()
print("MongoDB connection established")

# ========== MOVIE ANALYSIS ==========
print("\nGenerating movie analysis...")

# Get movie data
mongo_movies = db.db.detailed_movies.find({})
movies_df = pd.DataFrame(list(mongo_movies))
print(f"Retrieved {len(movies_df)} movies from MongoDB")

# Format data
if 'genres' in movies_df.columns and 'genre_names' not in movies_df.columns:
    print("Mapping 'genres' field to 'genre_names'")
    
    def extract_genre_names(genres):
        if not genres:
            return []
        names = []
        if isinstance(genres, list):
            for genre in genres:
                if isinstance(genre, dict) and 'name' in genre:
                    names.append(genre['name'])
                elif isinstance(genre, str):
                    names.append(genre)
        return names
    
    movies_df['genre_names'] = movies_df['genres'].apply(extract_genre_names)

# Extract year from release_date if available
if 'release_date' in movies_df.columns:
    movies_df['release_year'] = movies_df['release_date'].str[:4].astype('float', errors='ignore')

# 1. Genre Distribution
try:
    fig, ax = plt.subplots(figsize=(10, 6))
    genre_counts = {}
    
    # Count genres with error handling
    for genres in movies_df['genre_names']:
        if isinstance(genres, list):
            for genre in genres:
                if isinstance(genre, str):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
                elif isinstance(genre, dict) and 'name' in genre:
                    genre_name = genre['name']
                    genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
    
    # Sort and get top genres
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    if sorted_genres:
        genres = [g[0] for g in sorted_genres]
        counts = [g[1] for g in sorted_genres]
        
        # Create horizontal bar chart
        bars = ax.barh(genres, counts, color='#3498db')
        ax.set_title('Movie Genre Distribution', fontsize=16)
        ax.set_xlabel('Number of Movies')
        
        # Add count labels to bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 10, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                    ha='left', va='center', fontsize=10)
        
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        save_plot(fig, 'web/static/plots/movies/genre_distribution.png')
except Exception as e:
    print(f"Error creating genre distribution plot: {e}")

# 2. Rating Distribution
try:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(movies_df['vote_average'].dropna(), bins=20, color='#3498db', alpha=0.7, density=True)
    
    # Add a KDE line
    if len(movies_df['vote_average'].dropna()) > 10:
        try:
            kde_x = np.linspace(0, 10, 1000)
            kde = stats.gaussian_kde(movies_df['vote_average'].dropna())
            ax.plot(kde_x, kde(kde_x), 'r-', linewidth=2)
        except Exception as e:
            print(f"Error creating KDE: {e}")
    
    mean_rating = movies_df['vote_average'].mean()
    median_rating = movies_df['vote_average'].median()
    
    ax.axvline(mean_rating, color='#e74c3c', linestyle='--', 
              label=f'Mean Rating: {mean_rating:.2f}')
    ax.axvline(median_rating, color='#2ecc71', linestyle='--', 
              label=f'Median Rating: {median_rating:.2f}')
    
    ax.set_title('Movie Rating Distribution', fontsize=16)
    ax.set_xlabel('Rating')
    ax.set_ylabel('Density')
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    save_plot(fig, 'web/static/plots/movies/rating_distribution.png')
except Exception as e:
    print(f"Error creating rating distribution plot: {e}")

# 3. Popularity vs. Rating
try:
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(movies_df['vote_average'], movies_df['popularity'], 
                       alpha=0.5, c=movies_df['vote_count'], cmap='viridis', s=20)
    
    # Add colorbar for vote count
    cbar = plt.colorbar(scatter)
    cbar.set_label('Vote Count')
    
    movies_df['score'] = movies_df['popularity'] * movies_df['vote_average'] * movies_df['vote_count']

    # Label some interesting points
    for _, row in movies_df.nlargest(5, 'score').iterrows():
        ax.annotate(row['title'], (row['vote_average'], row['popularity']),
                   xytext=(5, 5), textcoords='offset points', fontsize=8)
                   
    ax.set_title('Movie Popularity vs. Rating', fontsize=16)
    ax.set_xlabel('Rating')
    ax.set_ylabel('Popularity')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_plot(fig, 'web/static/plots/movies/popularity_vs_rating.png')
except Exception as e:
    print(f"Error creating popularity vs rating plot: {e}")

# 4. Runtime Distribution
if 'runtime' in movies_df.columns:
    try:
        runtime_df = movies_df[movies_df['runtime'] > 0]
        if len(runtime_df) > 10:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(runtime_df['runtime'], bins=20, color='#3498db', alpha=0.7)
            
            mean_runtime = runtime_df['runtime'].mean()
            median_runtime = runtime_df['runtime'].median()
            
            ax.axvline(mean_runtime, color='#e74c3c', linestyle='--', 
                      label=f'Mean: {mean_runtime:.1f} min')
            ax.axvline(median_runtime, color='#2ecc71', linestyle='--', 
                      label=f'Median: {median_runtime:.1f} min')
            
            ax.set_title('Movie Runtime Distribution', fontsize=16)
            ax.set_xlabel('Runtime (minutes)')
            ax.set_ylabel('Number of Movies')
            ax.grid(alpha=0.3)
            ax.legend()
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/movies/runtime_distribution.png')
    except Exception as e:
        print(f"Error creating runtime distribution plot: {e}")

# 5. Budget vs Revenue
if 'budget' in movies_df.columns and 'revenue' in movies_df.columns:
    try:
        budget_df = movies_df[(movies_df['budget'] > 0) & (movies_df['revenue'] > 0)]
        if len(budget_df) > 10:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            scatter = ax.scatter(budget_df['budget'], budget_df['revenue'], 
                               alpha=0.6, c=budget_df['vote_average'], 
                               cmap='viridis', s=30)
            
            cbar = plt.colorbar(scatter)
            cbar.set_label('Rating')
            
            max_val = max(budget_df['budget'].max(), budget_df['revenue'].max())
            ax.plot([0, max_val], [0, max_val], 'r--', alpha=0.5, 
                   label='Budget = Revenue')
            
            for _, row in budget_df.nlargest(5, 'revenue').iterrows():
                ax.annotate(row['title'], (row['budget'], row['revenue']),
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
            
            ax.set_title('Movie Budget vs. Revenue', fontsize=16)
            ax.set_xlabel('Budget ($)')
            ax.set_ylabel('Revenue ($)')
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.grid(alpha=0.3)
            ax.legend()
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/movies/budget_revenue.png')
    except Exception as e:
        print(f"Error creating budget vs revenue plot: {e}")

# 6. Release Year Distribution
if 'release_year' in movies_df.columns:
    try:
        year_df = movies_df.dropna(subset=['release_year'])
        if not year_df.empty:
            year_df['release_year'] = pd.to_numeric(year_df['release_year'], errors='coerce')
            year_df = year_df.dropna(subset=['release_year'])
            
            year_counts = year_df['release_year'].value_counts().sort_index()
            recent_years = year_counts[year_counts.index >= 1950]
            
            if len(recent_years) > 0:
                fig, ax = plt.subplots(figsize=(12, 6))
                
                colors = plt.cm.viridis(np.linspace(0, 1, len(recent_years)))
                
                bars = ax.bar(recent_years.index, recent_years.values, color=colors, alpha=0.8)
                ax.set_title('Movies by Release Year (Since 1950)', fontsize=16)
                ax.set_xlabel('Release Year')
                ax.set_ylabel('Number of Movies')
                
                z = np.polyfit(recent_years.index, recent_years.values, 1)
                p = np.poly1d(z)
                ax.plot(recent_years.index, p(recent_years.index), "r--", linewidth=2)
                
                ax.grid(axis='y', alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                save_plot(fig, 'web/static/plots/movies/year_distribution.png')
    except Exception as e:
        print(f"Error creating year distribution plot: {e}")

# 7. Language Distribution
if 'original_language' in movies_df.columns:
    try:
        # Language bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        lang_counts = movies_df['original_language'].value_counts().head(10)
        
        bars = ax.bar(lang_counts.index, lang_counts.values, color='#3498db')
        ax.set_title('Top 10 Languages in Movies', fontsize=16)
        ax.set_xlabel('Language')
        ax.set_ylabel('Number of Movies')
        
        for i, v in enumerate(lang_counts.values):
            ax.text(i, v + 5, f'{v:,}', ha='center', fontsize=10)
            
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        save_plot(fig, 'web/static/plots/movies/language_distribution.png')
        
        # Language pie chart
        plt.figure(figsize=(10, 10))
        explode = [0.1 if i == 0 else 0 for i in range(len(lang_counts))]
        plt.pie(lang_counts.values, labels=lang_counts.index, autopct='%1.1f%%', 
                startangle=90, explode=explode, shadow=True, 
                colors=plt.cm.Paired(np.linspace(0, 1, len(lang_counts))))
        plt.axis('equal')
        plt.title('Top 10 Languages in Movies', fontsize=16)
        plt.tight_layout()
        save_plot(plt.gcf(), 'web/static/plots/movies/language_pie.png')
    except Exception as e:
        print(f"Error creating language plots: {e}")

# 8. Try to create word cloud if available
try:
    from wordcloud import WordCloud
    
    # Combine all movie titles
    all_titles = ' '.join(movies_df['title'].astype(str).tolist())
    
    # Create word cloud
    wordcloud = WordCloud(width=800, height=400, background_color='white',
                         max_words=200, contour_width=3, contour_color='steelblue',
                         colormap='viridis').generate(all_titles)
    
    # Display word cloud
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout()
    save_plot(plt.gcf(), 'web/static/plots/movies/title_wordcloud.png')
except ImportError:
    print("WordCloud not available - skipping word cloud generation")
except Exception as e:
    print(f"Error creating word cloud: {e}")

# Calculate statistics for export
# Create a weighted score for better ranking
movies_df['score'] = movies_df['popularity'] * movies_df['vote_average'] * movies_df['vote_count']

# Apply a minimum vote count threshold for highest rated
min_votes = 1000
qualified_movies = movies_df[movies_df['vote_count'] >= min_votes]

movie_stats = {
    'total_movies': int(len(movies_df)),
    'avg_rating': float(movies_df['vote_average'].mean()),
    'median_rating': float(movies_df['vote_average'].median()),
}

# Add top genres
if 'sorted_genres' in locals() and len(sorted_genres) >= 5:
    movie_stats['top_genres'] = [g[0] for g in sorted_genres[:5]]
else:
    movie_stats['top_genres'] = []

# Add highest rated movies
if not qualified_movies.empty:
    movie_stats['highest_rated'] = []
    for _, movie in qualified_movies.sort_values('vote_average', ascending=False).head(5).iterrows():
        movie_stats['highest_rated'].append({
            'id': str(movie['id']),
            'title': str(movie['title']),
            'vote_average': float(movie['vote_average']),
            'vote_count': int(movie['vote_count'])
        })

# Add most popular movies
movie_stats['most_popular'] = []
for _, movie in movies_df.sort_values('score', ascending=False).head(5).iterrows():
    movie_stats['most_popular'].append({
        'id': str(movie['id']),
        'title': str(movie['title']),
        'popularity': float(movie['popularity']),
        'vote_average': float(movie['vote_average']),
        'vote_count': int(movie['vote_count'])
    })

# Add runtime statistics if available
if 'runtime' in movies_df.columns:
    runtime_df = movies_df[movies_df['runtime'] > 0]
    if len(runtime_df) > 0:
        movie_stats['avg_runtime'] = float(runtime_df['runtime'].mean())
        
        longest_movies = []
        for _, movie in runtime_df.nlargest(5, 'runtime').iterrows():
            longest_movies.append({
                'id': str(movie['id']),
                'title': str(movie['title']),
                'runtime': int(movie['runtime'])
            })
        movie_stats['longest_movies'] = longest_movies
        
        shortest_movies = []
        for _, movie in runtime_df.nsmallest(5, 'runtime').iterrows():
            shortest_movies.append({
                'id': str(movie['id']),
                'title': str(movie['title']),
                'runtime': int(movie['runtime'])
            })
        movie_stats['shortest_movies'] = shortest_movies

# Add budget/revenue stats if available
if 'budget' in movies_df.columns and 'revenue' in movies_df.columns:
    budget_df = movies_df[(movies_df['budget'] > 0) & (movies_df['revenue'] > 0)]
    if len(budget_df) > 0:
        movie_stats['avg_budget'] = float(budget_df['budget'].mean())
        movie_stats['avg_revenue'] = float(budget_df['revenue'].mean())
        
        highest_budget = []
        for _, movie in budget_df.nlargest(5, 'budget').iterrows():
            highest_budget.append({
                'id': str(movie['id']),
                'title': str(movie['title']),
                'budget': float(movie['budget'])
            })
        movie_stats['highest_budget'] = highest_budget
        
        highest_revenue = []
        for _, movie in budget_df.nlargest(5, 'revenue').iterrows():
            highest_revenue.append({
                'id': str(movie['id']),
                'title': str(movie['title']),
                'revenue': float(movie['revenue'])
            })
        movie_stats['highest_revenue'] = highest_revenue

# Add production company statistics if available
if 'production_companies' in movies_df.columns:
    try:
        company_counts = {}
        for _, row in movies_df.iterrows():
            companies = row['production_companies']
            if isinstance(companies, list):
                for company in companies:
                    if isinstance(company, dict) and 'name' in company:
                        company_counts[company['name']] = company_counts.get(company['name'], 0) + 1
                    elif isinstance(company, str):
                        company_counts[company] = company_counts.get(company, 0) + 1
        
        if company_counts:
            sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            movie_stats['top_production_companies'] = [
                {'name': company, 'count': count} for company, count in sorted_companies
            ]
    except Exception as e:
        print(f"Error calculating production company statistics: {e}")

# Save movie stats to JSON
with open('web/static/data/movie_stats.json', 'w', encoding='utf-8') as f:
    json.dump(movie_stats, f, ensure_ascii=False)
print("Saved movie stats to JSON")

# ========== SERIES ANALYSIS ==========
print("\nGenerating series analysis...")

# Get series data
mongo_series = db.db.detailed_series.find({})
series_df = pd.DataFrame(list(mongo_series))
print(f"Retrieved {len(series_df)} series from MongoDB")

# Format data
if 'genres' in series_df.columns and 'genre_names' not in series_df.columns:
    print("Mapping 'genres' field to 'genre_names'")
    
    # Extract genre names (reuse function from above)
    series_df['genre_names'] = series_df['genres'].apply(extract_genre_names)

# Extract year from first_air_date if available
if 'first_air_date' in series_df.columns:
    series_df['start_year'] = series_df['first_air_date'].str[:4].astype('float', errors='ignore')

# Add similar plots for series (reusing the movie code pattern)
# 1. Genre Distribution
try:
    # Similar code as movie genre distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    genre_counts = {}
    for genres in series_df['genre_names']:
        if isinstance(genres, list):
            for genre in genres:
                if isinstance(genre, str):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    # Sort and get top genres
    sorted_series_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    if sorted_series_genres:
        genres = [g[0] for g in sorted_series_genres]
        counts = [g[1] for g in sorted_series_genres]
        
        # Create horizontal bar chart
        bars = ax.barh(genres, counts, color='#3498db')
        ax.set_title('TV Series Genre Distribution', fontsize=16)
        ax.set_xlabel('Number of Series')
        
        # Add count labels to bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 10, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                    ha='left', va='center', fontsize=10)
        
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        save_plot(fig, 'web/static/plots/series/genre_distribution.png')
except Exception as e:
    print(f"Error creating series genre distribution plot: {e}")

# 2. Rating Distribution
try:
    # Similar code as movie rating distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(series_df['vote_average'].dropna(), bins=20, color='#3498db', alpha=0.7, density=True)
    
    if len(series_df['vote_average'].dropna()) > 10:
        try:
            kde_x = np.linspace(0, 10, 1000)
            kde = stats.gaussian_kde(series_df['vote_average'].dropna())
            ax.plot(kde_x, kde(kde_x), 'r-', linewidth=2)
        except Exception as e:
            print(f"Error creating series KDE: {e}")
    
    mean_rating = series_df['vote_average'].mean()
    median_rating = series_df['vote_average'].median()
    
    ax.axvline(mean_rating, color='#e74c3c', linestyle='--', 
              label=f'Mean Rating: {mean_rating:.2f}')
    ax.axvline(median_rating, color='#2ecc71', linestyle='--', 
              label=f'Median Rating: {median_rating:.2f}')
    
    ax.set_title('TV Series Rating Distribution', fontsize=16)
    ax.set_xlabel('Rating')
    ax.set_ylabel('Density')
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    save_plot(fig, 'web/static/plots/series/rating_distribution.png')
except Exception as e:
    print(f"Error creating series rating distribution plot: {e}")

# 3. Popularity vs. Rating Scatter Plot for series
try:
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(series_df['vote_average'], series_df['popularity'], 
                       alpha=0.5, c=series_df['vote_count'], cmap='viridis', s=20)
    
    # Add colorbar for vote count
    cbar = plt.colorbar(scatter)
    cbar.set_label('Vote Count')

    series_df['score'] = series_df['popularity'] * series_df['vote_average'] * series_df['vote_count']
    
    # Label some interesting points
    for _, row in series_df.nlargest(5, 'score').iterrows():
        ax.annotate(row['name'], (row['vote_average'], row['popularity']),
                   xytext=(5, 5), textcoords='offset points', fontsize=8)
                   
    ax.set_title('TV Series Popularity vs. Rating', fontsize=16)
    ax.set_xlabel('Rating')
    ax.set_ylabel('Popularity')
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_plot(fig, 'web/static/plots/series/popularity_vs_rating.png')
except Exception as e:
    print(f"Error creating series popularity vs rating plot: {e}")

# 4. First Air Year Distribution
if 'start_year' in series_df.columns:
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        series_df['start_year'] = pd.to_numeric(series_df['start_year'], errors='coerce')
        year_counts = series_df['start_year'].value_counts().sort_index()
        
        # Filter recent years (e.g., last 30 years)
        recent_years = year_counts[year_counts.index >= 1990]
        
        if len(recent_years) > 0:
            # Use a colormap to show trend
            colors = plt.cm.viridis(np.linspace(0, 1, len(recent_years)))
            
            bars = ax.bar(recent_years.index, recent_years.values, color=colors, alpha=0.8)
            ax.set_title('TV Series by First Air Year (Since 1990)', fontsize=16)
            ax.set_xlabel('First Air Year')
            ax.set_ylabel('Number of Series')
            
            # Add trend line
            z = np.polyfit(recent_years.index, recent_years.values, 1)
            p = np.poly1d(z)
            ax.plot(recent_years.index, p(recent_years.index), "r--", linewidth=2)
            
            ax.grid(axis='y', alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/series/year_distribution.png')
    except Exception as e:
        print(f"Error creating series year distribution plot: {e}")

# 5. Language Distribution
if 'original_language' in series_df.columns:
    try:
        # Language bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        lang_counts = series_df['original_language'].value_counts().head(10)
        
        bars = ax.bar(lang_counts.index, lang_counts.values, color='#3498db')
        ax.set_title('Top 10 Languages in TV Series', fontsize=16)
        ax.set_xlabel('Language')
        ax.set_ylabel('Number of Series')
        
        # Add count labels
        for i, v in enumerate(lang_counts.values):
            ax.text(i, v + 5, f'{v:,}', ha='center', fontsize=10)
            
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        save_plot(fig, 'web/static/plots/series/language_distribution.png')
        
        # Language pie chart
        plt.figure(figsize=(10, 10))
        explode = [0.1 if i == 0 else 0 for i in range(len(lang_counts))]
        plt.pie(lang_counts.values, labels=lang_counts.index, autopct='%1.1f%%', 
                startangle=90, explode=explode, shadow=True, 
                colors=plt.cm.Paired(np.linspace(0, 1, len(lang_counts))))
        plt.axis('equal')
        plt.title('Top 10 Languages in TV Series', fontsize=16)
        plt.tight_layout()
        save_plot(plt.gcf(), 'web/static/plots/series/language_pie.png')
    except Exception as e:
        print(f"Error creating series language plots: {e}")

# 6. Number of Seasons Distribution
if 'number_of_seasons' in series_df.columns:
    try:
        # Filter to reasonable number of seasons
        seasons_df = series_df[series_df['number_of_seasons'] > 0]
        
        if len(seasons_df) > 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            seasons_count = seasons_df['number_of_seasons'].value_counts().sort_index()
            # Filter to reasonable number of seasons (e.g., up to 20)
            seasons_count = seasons_count[seasons_count.index <= 20]
            
            bars = ax.bar(seasons_count.index, seasons_count.values, color='#3498db')
            ax.set_title('Distribution of Number of Seasons', fontsize=16)
            ax.set_xlabel('Number of Seasons')
            ax.set_ylabel('Number of Series')
            
            # Add count labels
            for i, v in enumerate(seasons_count.values):
                ax.text(seasons_count.index[i], v + 5, f'{v:,}', ha='center', fontsize=10)
                
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/series/seasons_distribution.png')
    except Exception as e:
        print(f"Error creating seasons distribution plot: {e}")

# 7. Series Status (if available)
if 'status' in series_df.columns:
    try:
        status_counts = series_df['status'].value_counts().head(5)
        
        plt.figure(figsize=(10, 10))
        explode = [0.1 if i == 0 else 0 for i in range(len(status_counts))]
        plt.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', 
                startangle=90, explode=explode, shadow=True, 
                colors=plt.cm.tab10(np.linspace(0, 1, len(status_counts))))
        plt.axis('equal')
        plt.title('TV Series Status Distribution', fontsize=16)
        plt.tight_layout()
        save_plot(plt.gcf(), 'web/static/plots/series/status_pie.png')
    except Exception as e:
        print(f"Error creating status pie chart: {e}")

# 8. Episode Count vs. Season Count
if 'number_of_episodes' in series_df.columns and 'number_of_seasons' in series_df.columns:
    try:
        # Filter to series with both values > 0
        episodes_seasons_df = series_df[(series_df['number_of_episodes'] > 0) & (series_df['number_of_seasons'] > 0)]
        
        if len(episodes_seasons_df) > 5:  # Need enough data
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Create scatter plot
            scatter = ax.scatter(episodes_seasons_df['number_of_seasons'], 
                               episodes_seasons_df['number_of_episodes'], 
                               alpha=0.6, c=episodes_seasons_df['vote_average'], 
                               cmap='viridis', s=30)
            
            # Add colorbar for ratings
            cbar = plt.colorbar(scatter)
            cbar.set_label('Rating')
            
            # Add a line for typical episode count per season
            episodes_per_season = episodes_seasons_df['number_of_episodes'] / episodes_seasons_df['number_of_seasons']
            avg_episodes = episodes_per_season.median()
            x_range = np.array([1, episodes_seasons_df['number_of_seasons'].max()])
            ax.plot(x_range, avg_episodes * x_range, 'r--', alpha=0.5, 
                   label=f'Avg: {avg_episodes:.1f} episodes/season')
            
            # Label some notable series
            for _, row in episodes_seasons_df.nlargest(5, 'number_of_episodes').iterrows():
                ax.annotate(row['name'], (row['number_of_seasons'], row['number_of_episodes']),
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
            
            ax.set_title('TV Series: Episodes vs. Seasons', fontsize=16)
            ax.set_xlabel('Number of Seasons')
            ax.set_ylabel('Number of Episodes')
            ax.grid(alpha=0.3)
            ax.legend()
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/series/episodes_vs_seasons.png')
            
            # Create a histogram of episodes per season
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(episodes_per_season, bins=20, color='#3498db', alpha=0.7)
            
            ax.axvline(episodes_per_season.mean(), color='#e74c3c', linestyle='--', 
                      label=f'Mean: {episodes_per_season.mean():.1f}')
            ax.axvline(episodes_per_season.median(), color='#2ecc71', linestyle='--', 
                      label=f'Median: {episodes_per_season.median():.1f}')
            
            ax.set_title('Episodes per Season Distribution', fontsize=16)
            ax.set_xlabel('Episodes per Season')
            ax.set_ylabel('Number of Series')
            ax.grid(alpha=0.3)
            ax.legend()
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/series/episodes_per_season.png')
    except Exception as e:
        print(f"Error creating episodes vs seasons plots: {e}")

# 9. Networks Analysis (if available)
if 'networks' in series_df.columns:
    try:
        # Count series by network
        network_counts = {}
        for _, row in series_df.iterrows():
            networks = row['networks']
            if isinstance(networks, list):
                for network in networks:
                    if isinstance(network, dict) and 'name' in network:
                        network_counts[network['name']] = network_counts.get(network['name'], 0) + 1
                    elif isinstance(network, str):
                        network_counts[network] = network_counts.get(network, 0) + 1
        
        if network_counts:
            # Sort and get top networks
            sorted_networks = sorted(network_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            networks = [n[0] for n in sorted_networks]
            counts = [n[1] for n in sorted_networks]
            
            # Create horizontal bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(networks, counts, color='#3498db')
            ax.set_title('Top 10 TV Networks', fontsize=16)
            ax.set_xlabel('Number of Series')
            
            # Add count labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width + 5, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                        ha='left', va='center', fontsize=10)
            
            ax.grid(axis='x', alpha=0.3)
            plt.tight_layout()
            save_plot(fig, 'web/static/plots/series/network_distribution.png')
            
            # Also get average ratings by network
            network_ratings = {}
            for _, row in series_df.iterrows():
                networks = row['networks']
                if isinstance(networks, list) and isinstance(row['vote_average'], (int, float)):
                    for network in networks:
                        if isinstance(network, dict) and 'name' in network:
                            if network['name'] not in network_ratings:
                                network_ratings[network['name']] = []
                            network_ratings[network['name']].append(row['vote_average'])
                        elif isinstance(network, str):
                            if network not in network_ratings:
                                network_ratings[network] = []
                            network_ratings[network].append(row['vote_average'])
            
            # Calculate average ratings and filter to networks with enough data
            network_avg_ratings = {k: np.mean(v) for k, v in network_ratings.items() if len(v) >= 5}
            
            if network_avg_ratings:
                # Sort and get top rated networks
                sorted_ratings = sorted(network_avg_ratings.items(), key=lambda x: x[1], reverse=True)[:10]
                top_networks = [n[0] for n in sorted_ratings]
                avg_ratings = [n[1] for n in sorted_ratings]
                
                # Create horizontal bar chart
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.barh(top_networks, avg_ratings, color='#3498db')
                ax.set_title('Top 10 Networks by Average Rating', fontsize=16)
                ax.set_xlabel('Average Rating')
                
                # Add rating labels
                for i, bar in enumerate(bars):
                    width = bar.get_width()
                    ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{width:.2f}', 
                            ha='left', va='center', fontsize=10)
                
                ax.grid(axis='x', alpha=0.3)
                plt.tight_layout()
                save_plot(fig, 'web/static/plots/series/network_ratings.png')
    except Exception as e:
        print(f"Error creating network plots: {e}")
        
# 10. Word Cloud of Series Titles (if wordcloud is available)
try:
    from wordcloud import WordCloud
    
    # Combine all series titles
    all_titles = ' '.join(series_df['name'].astype(str).tolist())
    
    # Create word cloud
    wordcloud = WordCloud(width=800, height=400, background_color='white',
                         max_words=200, contour_width=3, contour_color='steelblue',
                         colormap='viridis').generate(all_titles)
    
    # Display word cloud
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout()
    save_plot(plt.gcf(), 'web/static/plots/series/title_wordcloud.png')
except ImportError:
    print("WordCloud not available - skipping series title word cloud")
except Exception as e:
    print(f"Error creating series word cloud: {e}")

# Calculate series statistics for export
series_df['score'] = series_df['popularity'] * series_df['vote_average'] * series_df['vote_count']

# Apply a minimum vote count threshold for highest rated
min_votes = 1000
qualified_series = series_df[series_df['vote_count'] >= min_votes]

series_stats = {
    'total_series': int(len(series_df)),
    'avg_rating': float(series_df['vote_average'].mean()),
    'median_rating': float(series_df['vote_average'].median()),
}

# Add top genres
if 'sorted_series_genres' in locals() and len(sorted_series_genres) >= 5:
    series_stats['top_genres'] = [g[0] for g in sorted_series_genres[:5]]
else:
    series_stats['top_genres'] = []

# Add highest rated series
if not qualified_series.empty:
    series_stats['highest_rated'] = []
    for _, series in qualified_series.sort_values('vote_average', ascending=False).head(5).iterrows():
        series_stats['highest_rated'].append({
            'id': str(series['id']),
            'name': str(series['name']),
            'vote_average': float(series['vote_average']),
            'vote_count': int(series['vote_count'])
        })

# Add most popular series
series_stats['most_popular'] = []
for _, series in series_df.sort_values('score', ascending=False).head(5).iterrows():
    series_stats['most_popular'].append({
        'id': str(series['id']),
        'name': str(series['name']),
        'popularity': float(series['popularity']),
        'vote_average': float(series['vote_average']),
        'vote_count': int(series['vote_count'])
    })

# Add seasons/episodes stats if available
if 'number_of_seasons' in series_df.columns:
    seasons_df = series_df[series_df['number_of_seasons'] > 0]
    if len(seasons_df) > 0:
        series_stats['avg_seasons'] = float(seasons_df['number_of_seasons'].mean())
        
        longest_running = []
        for _, series in seasons_df.nlargest(5, 'number_of_seasons').iterrows():
            longest_running.append({
                'id': str(series['id']),
                'name': str(series['name']),
                'number_of_seasons': int(series['number_of_seasons'])
            })
        series_stats['longest_running'] = longest_running

if 'number_of_episodes' in series_df.columns:
    episodes_df = series_df[series_df['number_of_episodes'] > 0]
    if len(episodes_df) > 0:
        series_stats['avg_episodes'] = float(episodes_df['number_of_episodes'].mean())
        
        most_episodes = []
        for _, series in episodes_df.nlargest(5, 'number_of_episodes').iterrows():
            most_episodes.append({
                'id': str(series['id']),
                'name': str(series['name']),
                'number_of_episodes': int(series['number_of_episodes'])
            })
        series_stats['most_episodes'] = most_episodes

# Add network stats if possible
if 'networks' in series_df.columns:
    try:
        network_counts = {}
        for _, row in series_df.iterrows():
            networks = row['networks']
            if isinstance(networks, list):
                for network in networks:
                    if isinstance(network, dict) and 'name' in network:
                        network_counts[network['name']] = network_counts.get(network['name'], 0) + 1
                    elif isinstance(network, str):
                        network_counts[network] = network_counts.get(network, 0) + 1
        
        if network_counts:
            sorted_networks = sorted(network_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            series_stats['top_networks'] = [
                {'name': network, 'count': count} for network, count in sorted_networks
            ]
    except Exception as e:
        print(f"Error calculating network statistics: {e}")

# Save series stats to JSON
with open('web/static/data/series_stats.json', 'w', encoding='utf-8') as f:
    json.dump(series_stats, f, ensure_ascii=False)
print("Saved series stats to JSON")

print("\nPlot generation complete!")
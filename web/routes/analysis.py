# web/routes/analysis.py
from flask import Blueprint, render_template, request, jsonify, current_app
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend which doesn't require GUI

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Database class
from src.data.database import Database

# Create blueprint
analysis_bp = Blueprint('analysis', __name__)

def get_plot_as_base64(fig, dpi=100):
    """Convert a matplotlib figure to a base64 string for HTML embedding"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return img_str

# Enhanced movie analysis route with direct database access
@analysis_bp.route('/movie-analysis')
def movie_analysis():
    try:
        # Connect to the database
        db = Database()
        
        # Get all movies directly from detailed_movies collection
        mongo_movies = db.db.detailed_movies.find({})
        
        # Convert to DataFrame
        movies_df = pd.DataFrame(list(mongo_movies))
        
        if len(movies_df) == 0:
            return "No movie data found in database", 404
        
        print(f"Retrieved {len(movies_df)} movies from MongoDB")
        
        # Check if 'genres' field exists and map it to 'genre_names' if needed
        if 'genres' in movies_df.columns and 'genre_names' not in movies_df.columns:
            print("Mapping 'genres' field to 'genre_names'")
            
            # MongoDB may store genres as objects with 'id' and 'name'
            # Extract just the names into a list for each movie
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
    except Exception as e:
        print(f"Error retrieving data from database: {e}")
        return f"Error retrieving data from database: {e}", 500
    
    # Verify we have the required columns for analysis
    required_cols = ['genre_names', 'vote_average', 'popularity', 'title']
    missing_cols = [col for col in required_cols if col not in movies_df.columns]
    if missing_cols:
        print(f"Missing columns for analysis: {missing_cols}")
        print(f"Available columns: {movies_df.columns.tolist()}")
        return "Analysis data is missing required fields. Please check your database.", 500
    
    # Generate plots
    plots = {}
    
    # 1. Genre Distribution
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        genre_counts = {}
        
        # Count genres with error handling
        for genres in movies_df['genre_names']:
            # Handle different formats of genre data
            if isinstance(genres, list):
                for genre in genres:
                    if isinstance(genre, str):
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
                    elif isinstance(genre, dict) and 'name' in genre:
                        genre_name = genre['name']
                        genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
            elif isinstance(genres, dict):
                # Handle case where genres might be a dictionary with names
                for _, genre_name in genres.items():
                    if isinstance(genre_name, str):
                        genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
                    elif isinstance(genre_name, dict) and 'name' in genre_name:
                        name = genre_name['name']
                        genre_counts[name] = genre_counts.get(name, 0) + 1
        
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
            plots['genre_distribution'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating genre distribution plot: {e}")
    
    # 2. Rating Distribution
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        # Use a kernel density estimate for a smoother histogram
        ax.hist(movies_df['vote_average'].dropna(), bins=20, color='#3498db', alpha=0.7, density=True)
        
        # Add a KDE line
        if len(movies_df['vote_average'].dropna()) > 10:  # Need enough data
            try:
                from scipy import stats
                kde_x = np.linspace(0, 10, 1000)
                kde = stats.gaussian_kde(movies_df['vote_average'].dropna())
                ax.plot(kde_x, kde(kde_x), 'r-', linewidth=2)
            except ImportError:
                print("scipy not available for KDE")
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
        plots['rating_distribution'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating rating distribution plot: {e}")
    
    # 3. Popularity vs. Rating Scatter Plot
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(movies_df['vote_average'], movies_df['popularity'], 
                           alpha=0.5, c=movies_df['vote_count'], cmap='viridis', s=20)
        
        # Add colorbar for vote count
        cbar = plt.colorbar(scatter)
        cbar.set_label('Vote Count')
        
        # Label some interesting points
        for _, row in movies_df.nlargest(5, 'popularity').iterrows():
            ax.annotate(row['title'], (row['vote_average'], row['popularity']),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
                       
        ax.set_title('Movie Popularity vs. Rating', fontsize=16)
        ax.set_xlabel('Rating')
        ax.set_ylabel('Popularity')
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plots['popularity_vs_rating'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating popularity vs rating plot: {e}")
    
    # 4. Runtime Distribution (if available)
    if 'runtime' in movies_df.columns:
        try:
            runtime_df = movies_df[movies_df['runtime'] > 0]
            if len(runtime_df) > 10:  # Need enough data
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
                plots['runtime_distribution'] = get_plot_as_base64(fig)
        except Exception as e:
            print(f"Error creating runtime distribution plot: {e}")
    
    # 5. Budget vs Revenue (if available)
    if 'budget' in movies_df.columns and 'revenue' in movies_df.columns:
        try:
            # Filter to movies with both budget and revenue > 0
            budget_df = movies_df[(movies_df['budget'] > 0) & (movies_df['revenue'] > 0)]
            if len(budget_df) > 10:  # Need enough data
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Create scatter plot with log scale
                scatter = ax.scatter(budget_df['budget'], budget_df['revenue'], 
                                   alpha=0.6, c=budget_df['vote_average'], 
                                   cmap='viridis', s=30)
                
                # Add colorbar for ratings
                cbar = plt.colorbar(scatter)
                cbar.set_label('Rating')
                
                # Add diagonal line (budget = revenue)
                max_val = max(budget_df['budget'].max(), budget_df['revenue'].max())
                ax.plot([0, max_val], [0, max_val], 'r--', alpha=0.5, 
                       label='Budget = Revenue')
                
                # Label some notable movies
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
                plots['budget_revenue'] = get_plot_as_base64(fig)
        except Exception as e:
            print(f"Error creating budget vs revenue plot: {e}")
    
    # 6. Release Year Distribution (if available)
    if 'release_year' in movies_df.columns:
        try:
            year_df = movies_df.dropna(subset=['release_year'])
            if not year_df.empty:
                year_df['release_year'] = pd.to_numeric(year_df['release_year'], errors='coerce')
                year_df = year_df.dropna(subset=['release_year'])
                
                year_counts = year_df['release_year'].value_counts().sort_index()
                # Filter to years after 1950
                recent_years = year_counts[year_counts.index >= 1950]
                
                if len(recent_years) > 0:
                    fig, ax = plt.subplots(figsize=(12, 6))
                    
                    # Use a colormap to show trend
                    from matplotlib.cm import viridis
                    colors = viridis(np.linspace(0, 1, len(recent_years)))
                    
                    bars = ax.bar(recent_years.index, recent_years.values, color=colors, alpha=0.8)
                    ax.set_title('Movies by Release Year (Since 1950)', fontsize=16)
                    ax.set_xlabel('Release Year')
                    ax.set_ylabel('Number of Movies')
                    
                    # Add trend line
                    z = np.polyfit(recent_years.index, recent_years.values, 1)
                    p = np.poly1d(z)
                    ax.plot(recent_years.index, p(recent_years.index), "r--", linewidth=2)
                    
                    ax.grid(axis='y', alpha=0.3)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    plots['year_distribution'] = get_plot_as_base64(fig)
        except Exception as e:
            print(f"Error creating year distribution plot: {e}")
    
    # 7. Language Distribution (if available)
    if 'original_language' in movies_df.columns:
        try:
            # Language bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            lang_counts = movies_df['original_language'].value_counts().head(10)
            
            bars = ax.bar(lang_counts.index, lang_counts.values, color='#3498db')
            ax.set_title('Top 10 Languages in Movies', fontsize=16)
            ax.set_xlabel('Language')
            ax.set_ylabel('Number of Movies')
            
            # Add count labels
            for i, v in enumerate(lang_counts.values):
                ax.text(i, v + 5, f'{v:,}', ha='center', fontsize=10)
                
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plots['language_distribution'] = get_plot_as_base64(fig)
            
            # Language pie chart
            plt.figure(figsize=(10, 10))
            explode = [0.1 if i == 0 else 0 for i in range(len(lang_counts))]
            plt.pie(lang_counts.values, labels=lang_counts.index, autopct='%1.1f%%', 
                    startangle=90, explode=explode, shadow=True, 
                    colors=plt.cm.Paired(np.linspace(0, 1, len(lang_counts))))
            plt.axis('equal')
            plt.title('Top 10 Languages in Movies', fontsize=16)
            plt.tight_layout()
            plots['language_pie'] = get_plot_as_base64(plt.gcf())
            plt.close()
        except Exception as e:
            print(f"Error creating language plots: {e}")
    
    # 8. Word Cloud of Movie Titles (if wordcloud is available)
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
        plots['title_wordcloud'] = get_plot_as_base64(plt.gcf())
        plt.close()
    except ImportError:
        print("WordCloud not available")
    except Exception as e:
        print(f"Error creating word cloud: {e}")
    
    # Calculate some statistics
    # First calculate a weighted score for better ranking
    movies_df['score'] = movies_df['popularity'] * movies_df['vote_average'] * movies_df['vote_count']
    
    # Apply a minimum vote count threshold for highest rated to avoid movies with few votes
    min_votes = 1000  # Minimum number of votes required
    qualified_movies = movies_df[movies_df['vote_count'] >= min_votes]
    
    stats = {
        'total_movies': len(movies_df),
        'avg_rating': movies_df['vote_average'].mean(),
        'median_rating': movies_df['vote_average'].median(),
        'top_genres': [g[0] for g in sorted_genres[:5]] if 'sorted_genres' in locals() and len(sorted_genres) >= 5 else [],
        'highest_rated': qualified_movies.sort_values('vote_average', ascending=False).head(5)[['id', 'title', 'vote_average', 'vote_count']].to_dict('records'),
        'most_popular': movies_df.sort_values('score', ascending=False).head(5)[['id', 'title', 'popularity', 'vote_average', 'vote_count']].to_dict('records')
    }
    
    # Add runtime statistics if available
    if 'runtime' in movies_df.columns:
        runtime_df = movies_df[movies_df['runtime'] > 0]
        if len(runtime_df) > 0:
            stats['avg_runtime'] = runtime_df['runtime'].mean()
            stats['longest_movies'] = runtime_df.nlargest(5, 'runtime')[['id', 'title', 'runtime']].to_dict('records')
            stats['shortest_movies'] = runtime_df.nsmallest(5, 'runtime')[['id', 'title', 'runtime']].to_dict('records')
    
    # Add budget and revenue statistics if available
    if 'budget' in movies_df.columns and 'revenue' in movies_df.columns:
        budget_df = movies_df[(movies_df['budget'] > 0) & (movies_df['revenue'] > 0)]
        if len(budget_df) > 0:
            stats['avg_budget'] = budget_df['budget'].mean()
            stats['avg_revenue'] = budget_df['revenue'].mean()
            stats['highest_budget'] = budget_df.nlargest(5, 'budget')[['id', 'title', 'budget']].to_dict('records')
            stats['highest_revenue'] = budget_df.nlargest(5, 'revenue')[['id', 'title', 'revenue']].to_dict('records')
    
    # Add runtime statistics if available
    if 'runtime' in movies_df.columns:
        runtime_df = movies_df[movies_df['runtime'] > 0]
        if len(runtime_df) > 0:
            stats['avg_runtime'] = runtime_df['runtime'].mean()
            stats['longest_movies'] = runtime_df.nlargest(5, 'runtime')[['id','title', 'runtime']].to_dict('records')
            stats['shortest_movies'] = runtime_df.nsmallest(5, 'runtime')[['id','title', 'runtime']].to_dict('records')
    
    # Add budget and revenue statistics if available
    if 'budget' in movies_df.columns and 'revenue' in movies_df.columns:
        budget_df = movies_df[(movies_df['budget'] > 0) & (movies_df['revenue'] > 0)]
        if len(budget_df) > 0:
            stats['avg_budget'] = budget_df['budget'].mean()
            stats['avg_revenue'] = budget_df['revenue'].mean()
            stats['highest_budget'] = budget_df.nlargest(5, 'budget')[['id','title', 'budget']].to_dict('records')
            stats['highest_revenue'] = budget_df.nlargest(5, 'revenue')[['id','title', 'revenue']].to_dict('records')
    
    # Add production company statistics if available
    if 'production_companies' in movies_df.columns:
        try:
            # Count movies by production company
            company_counts = {}
            for _, row in movies_df.iterrows():
                companies = row['production_companies']
                if isinstance(companies, list):
                    for company in companies:
                        if isinstance(company, dict) and 'name' in company:
                            company_counts[company['name']] = company_counts.get(company['name'], 0) + 1
                        elif isinstance(company, str):
                            company_counts[company] = company_counts.get(company, 0) + 1
            
            # Get top production companies
            if company_counts:
                sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                stats['top_production_companies'] = [{'name': company, 'count': count} for company, count in sorted_companies]
        except Exception as e:
            print(f"Error calculating production company statistics: {e}")
    
    return render_template('movie_analysis.html', plots=plots, stats=stats)

# Enhanced series analysis route with direct database access
@analysis_bp.route('/series-analysis')
def series_analysis():
    try:
        # Connect to the database
        db = Database()
        
        # Get all series directly from detailed_series collection
        mongo_series = db.db.detailed_series.find({})
        
        # Convert to DataFrame
        series_df = pd.DataFrame(list(mongo_series))
        
        if len(series_df) == 0:
            return "No series data found in database", 404
        
        print(f"Retrieved {len(series_df)} series from MongoDB")
        
        # Check if 'genres' field exists and map it to 'genre_names' if needed
        if 'genres' in series_df.columns and 'genre_names' not in series_df.columns:
            print("Mapping 'genres' field to 'genre_names'")
            
            # Extract genre names
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
            
            series_df['genre_names'] = series_df['genres'].apply(extract_genre_names)
            
        # Extract year from first_air_date if available
        if 'first_air_date' in series_df.columns:
            series_df['start_year'] = series_df['first_air_date'].str[:4].astype('float', errors='ignore')
    except Exception as e:
        print(f"Error retrieving data from database: {e}")
        return f"Error retrieving data from database: {e}", 500
    
    # Verify we have the required columns for analysis
    required_cols = ['genre_names', 'vote_average', 'popularity', 'name']
    missing_cols = [col for col in required_cols if col not in series_df.columns]
    if missing_cols:
        print(f"Missing columns for analysis: {missing_cols}")
        print(f"Available columns: {series_df.columns.tolist()}")
        return "Analysis data is missing required fields. Please check your database.", 500
    
    # Generate plots
    plots = {}
    
    # 1. Genre Distribution
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        genre_counts = {}
        for genres in series_df['genre_names']:
            if isinstance(genres, list):
                for genre in genres:
                    if isinstance(genre, str):
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Sort and get top genres
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        if sorted_genres:
            genres = [g[0] for g in sorted_genres]
            counts = [g[1] for g in sorted_genres]
            
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
            plots['genre_distribution'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating genre distribution plot: {e}")
    
    # 2. Rating Distribution
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        # Use a kernel density estimate for a smoother histogram
        ax.hist(series_df['vote_average'].dropna(), bins=20, color='#3498db', alpha=0.7, density=True)
        
        # Add a KDE line
        if len(series_df['vote_average'].dropna()) > 10:  # Need enough data
            try:
                from scipy import stats
                kde_x = np.linspace(0, 10, 1000)
                kde = stats.gaussian_kde(series_df['vote_average'].dropna())
                ax.plot(kde_x, kde(kde_x), 'r-', linewidth=2)
            except ImportError:
                print("scipy not available for KDE")
            except Exception as e:
                print(f"Error creating KDE: {e}")
        
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
        plots['rating_distribution'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating rating distribution plot: {e}")
    
    # 3. First Air Year Distribution
    try:
        if 'start_year' in series_df.columns:
            fig, ax = plt.subplots(figsize=(12, 6))
            series_df['start_year'] = pd.to_numeric(series_df['start_year'], errors='coerce')
            year_counts = series_df['start_year'].value_counts().sort_index()
            
            # Filter recent years (e.g., last 30 years)
            recent_years = year_counts[year_counts.index >= 1990]
            
            if len(recent_years) > 0:
                # Use a colormap to show trend
                from matplotlib.cm import viridis
                colors = viridis(np.linspace(0, 1, len(recent_years)))
                
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
                plots['year_distribution'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating year distribution plot: {e}")
    
    # 4. Language Distribution
    try:
        if 'original_language' in series_df.columns:
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
            plots['language_distribution'] = get_plot_as_base64(fig)
            
            # Language pie chart
            plt.figure(figsize=(10, 10))
            explode = [0.1 if i == 0 else 0 for i in range(len(lang_counts))]
            plt.pie(lang_counts.values, labels=lang_counts.index, autopct='%1.1f%%', 
                    startangle=90, explode=explode, shadow=True, 
                    colors=plt.cm.Paired(np.linspace(0, 1, len(lang_counts))))
            plt.axis('equal')
            plt.title('Top 10 Languages in TV Series', fontsize=16)
            plt.tight_layout()
            plots['language_pie'] = get_plot_as_base64(plt.gcf())
            plt.close()
    except Exception as e:
        print(f"Error creating language plots: {e}")
    
    # 5. Number of Seasons Distribution
    try:
        if 'number_of_seasons' in series_df.columns:
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
                plots['seasons_distribution'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating seasons distribution plot: {e}")
    
    # 6. Series Status (if available)
    try:
        if 'status' in series_df.columns:
            status_counts = series_df['status'].value_counts().head(5)
            
            plt.figure(figsize=(10, 10))
            explode = [0.1 if i == 0 else 0 for i in range(len(status_counts))]
            plt.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', 
                    startangle=90, explode=explode, shadow=True, 
                    colors=plt.cm.tab10(np.linspace(0, 1, len(status_counts))))
            plt.axis('equal')
            plt.title('TV Series Status Distribution', fontsize=16)
            plt.tight_layout()
            plots['status_pie'] = get_plot_as_base64(plt.gcf())
            plt.close()
    except Exception as e:
        print(f"Error creating status pie chart: {e}")
    
    # 7. Episode Count vs. Season Count
    try:
        if 'number_of_episodes' in series_df.columns and 'number_of_seasons' in series_df.columns:
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
                plots['episodes_vs_seasons'] = get_plot_as_base64(fig)
                
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
                plots['episodes_per_season'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating episodes vs seasons plots: {e}")
    
    # 8. Popularity vs. Rating Scatter Plot
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(series_df['vote_average'], series_df['popularity'], 
                           alpha=0.5, c=series_df['vote_count'], cmap='viridis', s=20)
        
        # Add colorbar for vote count
        cbar = plt.colorbar(scatter)
        cbar.set_label('Vote Count')
        
        # Label some interesting points
        for _, row in series_df.nlargest(5, 'popularity').iterrows():
            ax.annotate(row['name'], (row['vote_average'], row['popularity']),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
                       
        ax.set_title('TV Series Popularity vs. Rating', fontsize=16)
        ax.set_xlabel('Rating')
        ax.set_ylabel('Popularity')
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plots['popularity_vs_rating'] = get_plot_as_base64(fig)
    except Exception as e:
        print(f"Error creating popularity vs rating plot: {e}")
    
    # 9. Networks Analysis (if available)
    try:
        if 'networks' in series_df.columns:
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
                plots['network_distribution'] = get_plot_as_base64(fig)
                
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
                    plots['network_ratings'] = get_plot_as_base64(fig)
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
        plots['title_wordcloud'] = get_plot_as_base64(plt.gcf())
        plt.close()
    except ImportError:
        print("WordCloud not available")
    except Exception as e:
        print(f"Error creating word cloud: {e}")
    
    # For the series_analysis function, make a similar change:

     # Calculate statistics
    # First calculate a weighted score for better ranking
    series_df['score'] = series_df['popularity'] * series_df['vote_average'] * series_df['vote_count']
    
    # Apply a minimum vote count threshold for highest rated to avoid series with few votes
    min_votes = 1000  # Minimum number of votes required
    qualified_series = series_df[series_df['vote_count'] >= min_votes]
    
    stats = {
        'total_series': len(series_df),
        'avg_rating': series_df['vote_average'].mean(),
        'median_rating': series_df['vote_average'].median(),
        'top_genres': [g[0] for g in sorted_genres[:5]] if 'sorted_genres' in locals() and len(sorted_genres) >= 5 else [],
        'highest_rated': qualified_series.sort_values('vote_average', ascending=False).head(5)[['id', 'name', 'vote_average', 'vote_count']].to_dict('records'),
        'most_popular': series_df.sort_values('score', ascending=False).head(5)[['id', 'name', 'popularity', 'vote_average', 'vote_count']].to_dict('records')
    }
    
    # Add episode/season stats if available
    if 'number_of_seasons' in series_df.columns:
        seasons_df = series_df[series_df['number_of_seasons'] > 0]
        if len(seasons_df) > 0:
            stats.update({
                'avg_seasons': seasons_df['number_of_seasons'].mean(),
                'longest_running': seasons_df.nlargest(5, 'number_of_seasons')[['id', 'name', 'number_of_seasons']].to_dict('records')
            })
    
    if 'number_of_episodes' in series_df.columns:
        episodes_df = series_df[series_df['number_of_episodes'] > 0]
        if len(episodes_df) > 0:
            stats.update({
                'avg_episodes': episodes_df['number_of_episodes'].mean(),
                'most_episodes': episodes_df.nlargest(5, 'number_of_episodes')[['id', 'name', 'number_of_episodes']].to_dict('records')
            })
    
    # Add episode/season stats if available
    if 'number_of_seasons' in series_df.columns:
        seasons_df = series_df[series_df['number_of_seasons'] > 0]
        if len(seasons_df) > 0:
            stats.update({
                'avg_seasons': seasons_df['number_of_seasons'].mean(),
                'longest_running': seasons_df.nlargest(5, 'number_of_seasons')[['id','name', 'number_of_seasons']].to_dict('records')
            })
    
    if 'number_of_episodes' in series_df.columns:
        episodes_df = series_df[series_df['number_of_episodes'] > 0]
        if len(episodes_df) > 0:
            stats.update({
                'avg_episodes': episodes_df['number_of_episodes'].mean(),
                'most_episodes': episodes_df.nlargest(5, 'number_of_episodes')[['id','name', 'number_of_episodes']].to_dict('records')
            })
    
    # Get top networks if available
    if 'networks' in series_df.columns and 'network_counts' in locals() and network_counts:
        sorted_networks = sorted(network_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats['top_networks'] = [{'name': network, 'count': count} for network, count in sorted_networks]
    
    return render_template('series_analysis.html', plots=plots, stats=stats)
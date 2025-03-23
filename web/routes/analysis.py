# web/routes/analysis.py (updated version)
from flask import Blueprint, render_template, request, jsonify, current_app, url_for
import os
import json
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Database class
from src.data.database import Database

# Create blueprint
analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/movie-analysis')
def movie_analysis():
    try:
        # Load pre-generated stats from JSON
        stats_file = os.path.join(current_app.root_path, 'static/data/movie_stats.json')
        
        if not os.path.exists(stats_file):
            return "Movie analysis data not found. Please run the plot generation script locally first.", 404
            
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
        
        # Create plots dictionary with static file URLs
        plots = {}
        plots_dir = os.path.join(current_app.root_path, 'static/plots/movies')
        
        if os.path.exists(plots_dir):
            for plot_file in os.listdir(plots_dir):
                if plot_file.endswith('.png'):
                    plot_name = os.path.splitext(plot_file)[0]
                    plots[plot_name] = url_for('static', filename=f'plots/movies/{plot_file}')
        
        return render_template('movie_analysis.html', plots=plots, stats=stats)
    except Exception as e:
        current_app.logger.error(f"Error loading movie analysis data: {e}")
        return f"Error loading movie analysis data: {e}", 500

@analysis_bp.route('/series-analysis')
def series_analysis():
    try:
        # Load pre-generated stats from JSON
        stats_file = os.path.join(current_app.root_path, 'static/data/series_stats.json')
        
        if not os.path.exists(stats_file):
            return "Series analysis data not found. Please run the plot generation script locally first.", 404
            
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
        
        # Create plots dictionary with static file URLs
        plots = {}
        plots_dir = os.path.join(current_app.root_path, 'static/plots/series')
        
        if os.path.exists(plots_dir):
            for plot_file in os.listdir(plots_dir):
                if plot_file.endswith('.png'):
                    plot_name = os.path.splitext(plot_file)[0]
                    plots[plot_name] = url_for('static', filename=f'plots/series/{plot_file}')
        
        return render_template('series_analysis.html', plots=plots, stats=stats)
    except Exception as e:
        current_app.logger.error(f"Error loading series analysis data: {e}")
        return f"Error loading series analysis data: {e}", 500
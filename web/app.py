# web/app.py
from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
import logging
import time
import sys

# Add the current directory and parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

# Load environment variables - using a cross-platform path
env_path = os.path.join(parent_dir, "data", ".env")
load_dotenv(dotenv_path=env_path)

# Import the JSONDatabase to initialize it at startup
from src.data.json_database import JSONDatabase

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    app.config['MODEL_PATH'] = os.path.join(parent_dir, 'models')
    
    # Preload the database at startup
    start_time = time.time()
    print("Preloading database...")
    data_dir = os.path.join(parent_dir, "data", "processed")
    db = JSONDatabase(data_dir=data_dir)
    end_time = time.time()
    print(f"Database loaded in {end_time - start_time:.2f} seconds")
    
    # Configure logging
    if not app.debug:
        file_handler = logging.FileHandler('app.log')
        file_handler.setLevel(logging.ERROR)
        app.logger.addHandler(file_handler)
    
    # Explicitly import the routes from web.routes (using the full path)
    from web.routes.analysis import analysis_bp
    from web.routes.recommender import recommender_bp
    
    app.register_blueprint(analysis_bp)
    app.register_blueprint(recommender_bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        app.logger.warning(f"Page not found: {request.path}")
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Server error: {str(e)}", exc_info=True)
        return render_template('500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the error
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        # Return 500 page
        return render_template('500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
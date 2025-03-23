# web/app.py
from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
import logging

import sys
# Add the web directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)  # Add web directory to path

# Load environment variables
load_dotenv(dotenv_path="..\\data\\.env")

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    app.config['MODEL_PATH'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
    
    # Configure logging
    if not app.debug:
        file_handler = logging.FileHandler('app.log')
        file_handler.setLevel(logging.ERROR)
        app.logger.addHandler(file_handler)
    
    # Register blueprints
    from routes.analysis import analysis_bp
    from routes.recommender import recommender_bp
    
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
    
    # Load models when app starts
    with app.app_context():
        from web.routes.recommender import load_models  # Import your function
        load_models()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
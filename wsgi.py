import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app factory function
from web.app import create_app

# Create the application
app = create_app()

if __name__ == "__main__":
    app.run()
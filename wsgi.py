import os
import sys

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.abspath(__file__))

# Add project root and web directory to Python path
sys.path.append(project_root)

# Import the app factory function from the web folder
from web.app import create_app

# Create the application
app = create_app()

if __name__ == "__main__":
    app.run()
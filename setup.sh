#!/bin/bash

# Create models directory
mkdir -p /var/render/service/models

# Install AWS CLI
pip install awscli

# Set AWS credentials
export AWS_ACCESS_KEY_ID=AKIA4SYAMY6HF3WG74WF
export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY

# Download models
echo "Downloading models from S3..."
aws s3 cp s3://imdb-recommender-models/movie_recommender.joblib /var/render/service/models/movie_recommender.joblib
aws s3 cp s3://imdb-recommender-models/series_recommender.joblib /var/render/service/models/series_recommender.joblib
echo "Models downloaded successfully!"
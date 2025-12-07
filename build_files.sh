#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Download spacy model (optional, for NLP features)
python -m spacy download en_core_web_sm || true

# Collect static files
python manage.py collectstatic --noinput

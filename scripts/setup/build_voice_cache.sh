#!/bin/bash

# Voice Preview Cache Builder
# This script generates all voice preview files for the application

set -e

echo "🎵 Voice Preview Cache Builder"
echo "=============================="
echo

# Check if we're in the right directory
if [ ! -f "../../README.md" ]; then
    echo "❌ Error: Please run this script from scripts/setup/ directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

# Check if Google Cloud TTS library is installed
if ! python3 -c "import google.cloud.texttospeech" 2>/dev/null; then
    echo "⚠️  Warning: google-cloud-texttospeech library not found"
    echo
    echo "Installing Google Cloud Text-to-Speech library..."
    pip3 install google-cloud-texttospeech
    echo
fi

# Check for credentials
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable not set"
    echo
    echo "Make sure you have set up Google Cloud TTS API credentials:"
    echo "1. Create a service account key file"
    echo "2. Export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create preview cache directory
echo "📁 Creating preview cache directory..."
mkdir -p ../../resources/preview_cache

# Run the voice preview generator
echo "🎵 Generating voice previews..."
echo
python3 generate_voice_previews.py

echo
echo "✅ Voice preview cache build complete!"
echo "📁 Files are located in: ../../resources/preview_cache/"
echo
echo "The voice preview files are now ready to ship with the application." 
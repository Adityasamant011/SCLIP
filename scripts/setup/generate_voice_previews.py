#!/usr/bin/env python3
"""
Voice Preview Generator Script

This script generates voice preview MP3 files for all available voices.
The generated files should be placed in resources/preview_cache/ directory.

Requirements:
- Google Cloud TTS API credentials
- google-cloud-texttospeech library

Usage:
    python generate_voice_previews.py

The script will generate voice_{voice_name}.mp3 files for all 68 English voices.
"""

import os
import sys
from pathlib import Path

try:
    from google.cloud import texttospeech
except ImportError:
    print("Error: google-cloud-texttospeech library not found.")
    print("Install with: pip install google-cloud-texttospeech")
    sys.exit(1)

# All 68 English voices
VOICES = [
    # English (US) - Neural2 voices
    ("en-US-Neural2-A", "en-US"),
    ("en-US-Neural2-C", "en-US"),
    ("en-US-Neural2-D", "en-US"),
    ("en-US-Neural2-E", "en-US"),
    ("en-US-Neural2-F", "en-US"),
    ("en-US-Neural2-G", "en-US"),
    ("en-US-Neural2-H", "en-US"),
    ("en-US-Neural2-I", "en-US"),
    ("en-US-Neural2-J", "en-US"),
    
    # English (US) - Wavenet voices
    ("en-US-Wavenet-A", "en-US"),
    ("en-US-Wavenet-B", "en-US"),
    ("en-US-Wavenet-C", "en-US"),
    ("en-US-Wavenet-D", "en-US"),
    ("en-US-Wavenet-E", "en-US"),
    ("en-US-Wavenet-F", "en-US"),
    ("en-US-Wavenet-G", "en-US"),
    ("en-US-Wavenet-H", "en-US"),
    ("en-US-Wavenet-I", "en-US"),
    ("en-US-Wavenet-J", "en-US"),
    
    # English (US) - Standard voices
    ("en-US-Standard-A", "en-US"),
    ("en-US-Standard-B", "en-US"),
    ("en-US-Standard-C", "en-US"),
    ("en-US-Standard-D", "en-US"),
    ("en-US-Standard-E", "en-US"),
    ("en-US-Standard-F", "en-US"),
    ("en-US-Standard-G", "en-US"),
    ("en-US-Standard-H", "en-US"),
    ("en-US-Standard-I", "en-US"),
    ("en-US-Standard-J", "en-US"),
    
    # English (UK) - Neural2 voices
    ("en-GB-Neural2-A", "en-GB"),
    ("en-GB-Neural2-B", "en-GB"),
    ("en-GB-Neural2-C", "en-GB"),
    ("en-GB-Neural2-D", "en-GB"),
    ("en-GB-Neural2-F", "en-GB"),
    
    # English (UK) - Wavenet voices
    ("en-GB-Wavenet-A", "en-GB"),
    ("en-GB-Wavenet-B", "en-GB"),
    ("en-GB-Wavenet-C", "en-GB"),
    ("en-GB-Wavenet-D", "en-GB"),
    ("en-GB-Wavenet-F", "en-GB"),
    
    # English (UK) - Standard voices
    ("en-GB-Standard-A", "en-GB"),
    ("en-GB-Standard-B", "en-GB"),
    ("en-GB-Standard-C", "en-GB"),
    ("en-GB-Standard-D", "en-GB"),
    ("en-GB-Standard-F", "en-GB"),
    
    # English (Australia) - Neural2 voices
    ("en-AU-Neural2-A", "en-AU"),
    ("en-AU-Neural2-B", "en-AU"),
    ("en-AU-Neural2-C", "en-AU"),
    ("en-AU-Neural2-D", "en-AU"),
    
    # English (Australia) - Wavenet voices
    ("en-AU-Wavenet-A", "en-AU"),
    ("en-AU-Wavenet-B", "en-AU"),
    ("en-AU-Wavenet-C", "en-AU"),
    ("en-AU-Wavenet-D", "en-AU"),
    
    # English (Australia) - Standard voices
    ("en-AU-Standard-A", "en-AU"),
    ("en-AU-Standard-B", "en-AU"),
    ("en-AU-Standard-C", "en-AU"),
    ("en-AU-Standard-D", "en-AU"),
    
    # English (India) - Neural2 voices
    ("en-IN-Neural2-A", "en-IN"),
    ("en-IN-Neural2-B", "en-IN"),
    ("en-IN-Neural2-C", "en-IN"),
    ("en-IN-Neural2-D", "en-IN"),
    
    # English (India) - Wavenet voices
    ("en-IN-Wavenet-A", "en-IN"),
    ("en-IN-Wavenet-B", "en-IN"),
    ("en-IN-Wavenet-C", "en-IN"),
    ("en-IN-Wavenet-D", "en-IN"),
    
    # English (India) - Standard voices
    ("en-IN-Standard-A", "en-IN"),
    ("en-IN-Standard-B", "en-IN"),
    ("en-IN-Standard-C", "en-IN"),
    ("en-IN-Standard-D", "en-IN"),
]

PREVIEW_TEXT = "Hello, this is a preview of my voice. I hope you like how I sound!"

def generate_voice_previews():
    """Generate voice preview files for all voices."""
    
    # Initialize the TTS client
    try:
        client = texttospeech.TextToSpeechClient()
    except Exception as e:
        print(f"\n❌ Error initializing Google Cloud TTS client: {e}")
        print("\nCould not find or load Google Cloud credentials.")
        print("Please ensure you have set up your credentials correctly:")
        print("1. A 'credentials' folder should exist in your project root.")
        print("2. Place your downloaded service account JSON key in this folder.")
        print("3. Rename the key file to 'gcp-creds.json'.")
        print("4. Make sure the GOOGLE_APPLICATION_CREDENTIALS environment variable is set to the full path of this file.")
        return False
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    cache_dir = project_root / "resources" / "preview_cache"
    
    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎵 Generating voice previews...")
    print(f"📁 Output directory: {cache_dir}")
    print(f"🎯 Total voices: {len(VOICES)}")
    print()
    
    generated_count = 0
    failed_count = 0
    
    for voice_name, language_code in VOICES:
        output_file = cache_dir / f"voice_{voice_name}.mp3"
        
        # Skip if file already exists
        if output_file.exists():
            print(f"⏭️  Skipping {voice_name} (file exists)")
            continue
            
        try:
            # Set up the synthesis request
            synthesis_input = texttospeech.SynthesisInput(text=PREVIEW_TEXT)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Write the audio content to file
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            
            print(f"✅ Generated {voice_name}")
            generated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to generate {voice_name}: {e}")
            failed_count += 1
    
    print()
    print(f"🎉 Voice preview generation complete!")
    print(f"✅ Generated: {generated_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📁 Files saved to: {cache_dir}")
    
    return failed_count == 0

if __name__ == "__main__":
    print("🎵 Voice Preview Generator")
    print("=" * 40)
    print()
    
    success = generate_voice_previews()
    
    if success:
        print("\n🚀 All voice previews generated successfully!")
        print("You can now use the voice preview system in the application.")
    else:
        print("\n⚠️  Some voice previews failed to generate.")
        print("Check your Google Cloud TTS API setup and try again.")
        sys.exit(1) 
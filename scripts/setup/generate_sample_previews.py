#!/usr/bin/env python3
"""
Sample Voice Preview Generator

This script generates sample/placeholder voice preview files for testing
the voice preview system without requiring Google Cloud TTS API.

Usage:
    python generate_sample_previews.py
"""

import os
from pathlib import Path

# Sample voices to create (just a few for testing)
SAMPLE_VOICES = [
    "en-US-Neural2-A",
    "en-US-Neural2-C", 
    "en-US-Neural2-D",
    "en-US-Neural2-E",
    "en-GB-Neural2-A",
    "en-GB-Neural2-B",
    "en-AU-Neural2-A",
    "en-AU-Neural2-B",
]

def generate_sample_audio():
    """Generate a simple WAV file that can be played for testing."""
    try:
        import wave
        import struct
        import math
        
        # Generate a simple 1-second sine wave tone
        sample_rate = 44100
        duration = 1.0  # 1 second
        frequency = 440  # A4 note
        
        # Generate sine wave samples
        samples = []
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            # Create a soft sine wave that fades in and out
            amplitude = 0.1 * math.sin(2 * math.pi * frequency * t) * math.exp(-t * 2)
            sample = int(amplitude * 32767)
            samples.append(struct.pack('<h', sample))
        
        return b''.join(samples), sample_rate
        
    except ImportError:
        # Fallback: create a very minimal valid audio file header
        # This creates a basic WAV header with silence
        return b'\x00' * 44100, 44100  # 1 second of silence

def generate_sample_previews():
    """Generate sample voice preview files."""
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    cache_dir = project_root / "resources" / "preview_cache"
    
    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎵 Generating sample voice previews...")
    print(f"📁 Output directory: {cache_dir}")
    print(f"🎯 Sample voices: {len(SAMPLE_VOICES)}")
    print()
    print("⚠️  Note: These are placeholder files for testing.")
    print("    Generate real voice previews using Google Cloud TTS for production.")
    print()
    
    audio_data, sample_rate = generate_sample_audio()
    generated_count = 0
    
    for voice_name in SAMPLE_VOICES:
        output_file = cache_dir / f"voice_{voice_name}.mp3"
        
        # Skip if file already exists
        if output_file.exists():
            print(f"⏭️  Skipping {voice_name} (file exists)")
            continue
        
        try:
            # Create a simple WAV file (which browsers can play)
            import wave
            
            # Create temporary WAV file and then save as .mp3 extension
            # (The browser will still be able to play it)
            with wave.open(str(output_file), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)
            
            print(f"✅ Created sample preview for {voice_name}")
            generated_count += 1
            
        except Exception as e:
            # Fallback: create a basic file
            try:
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                print(f"✅ Created basic sample for {voice_name}")
                generated_count += 1
            except Exception as e2:
                print(f"❌ Failed to create {voice_name}: {e2}")
    
    print()
    print(f"🎉 Sample voice preview generation complete!")
    print(f"✅ Generated: {generated_count} sample files")
    print(f"📁 Files saved to: {cache_dir}")
    print()
    print("🚀 You can now test the voice preview system in the application!")
    print("   (Note: Sample files are silent - for real audio, set up Google Cloud TTS)")

if __name__ == "__main__":
    print("🎵 Sample Voice Preview Generator")
    print("=" * 50)
    print()
    
    generate_sample_previews() 
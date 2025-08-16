# Voice Preview Cache

This directory contains pre-generated voice preview MP3 files for the 68+ English voices available in the application.

## File Format

Voice preview files should be named using the pattern:
```
voice_{voice_name}.mp3
```

For example:
- `voice_en-US-Neural2-A.mp3`
- `voice_en-GB-Wavenet-C.mp3`
- `voice_en-AU-Standard-B.mp3`

## Generating Voice Previews

To generate all voice preview files, use the Python script:

```bash
cd scripts/setup
python generate_voice_previews.py
```

This will create all 68 voice preview files in this directory.

## Required Voice Files

The application expects preview files for these voices:

### English (US) - Neural2
- voice_en-US-Neural2-A.mp3 through voice_en-US-Neural2-J.mp3

### English (US) - Wavenet  
- voice_en-US-Wavenet-A.mp3 through voice_en-US-Wavenet-J.mp3

### English (US) - Standard
- voice_en-US-Standard-A.mp3 through voice_en-US-Standard-J.mp3

### English (UK) - Neural2
- voice_en-GB-Neural2-A.mp3, voice_en-GB-Neural2-B.mp3, voice_en-GB-Neural2-C.mp3, voice_en-GB-Neural2-D.mp3, voice_en-GB-Neural2-F.mp3

### English (UK) - Wavenet
- voice_en-GB-Wavenet-A.mp3, voice_en-GB-Wavenet-B.mp3, voice_en-GB-Wavenet-C.mp3, voice_en-GB-Wavenet-D.mp3, voice_en-GB-Wavenet-F.mp3

### English (UK) - Standard
- voice_en-GB-Standard-A.mp3, voice_en-GB-Standard-B.mp3, voice_en-GB-Standard-C.mp3, voice_en-GB-Standard-D.mp3, voice_en-GB-Standard-F.mp3

### English (Australia) - Neural2, Wavenet, Standard
- voice_en-AU-Neural2-A.mp3 through voice_en-AU-Neural2-D.mp3
- voice_en-AU-Wavenet-A.mp3 through voice_en-AU-Wavenet-D.mp3
- voice_en-AU-Standard-A.mp3 through voice_en-AU-Standard-D.mp3

### English (India) - Neural2, Wavenet, Standard
- voice_en-IN-Neural2-A.mp3 through voice_en-IN-Neural2-D.mp3
- voice_en-IN-Wavenet-A.mp3 through voice_en-IN-Wavenet-D.mp3
- voice_en-IN-Standard-A.mp3 through voice_en-IN-Standard-D.mp3

## Preview Text

All voice previews use the text:
> "Hello, this is a preview of my voice. I hope you like how I sound!"

This provides a consistent way for users to compare different voices. 
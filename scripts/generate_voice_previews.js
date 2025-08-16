#!/usr/bin/env node

/**
 * Voice Preview Generator - Redirects to Python script
 * 
 * Voice previews are now generated using the Python script in scripts/setup/
 * This provides better control and error handling for TTS generation.
 */

console.log('🎵 Voice Preview Generator');
console.log('==========================');
console.log('');
console.log('Voice previews are now generated using the Python script.');
console.log('');
console.log('To generate voice preview files:');
console.log('');
console.log('1. Set up Google Cloud TTS API credentials');
console.log('2. Install Python dependencies:');
console.log('   pip install google-cloud-texttospeech');
console.log('');
console.log('3. Run the generator script:');
console.log('   cd scripts/setup');
console.log('   python generate_voice_previews.py');
console.log('');
console.log('4. Voice files will be saved to:');
console.log('   resources/preview_cache/voice_{voice_name}.mp3');
console.log('');
console.log('The generated files are shipped with the application');
console.log('for instant voice preview playback.'); 
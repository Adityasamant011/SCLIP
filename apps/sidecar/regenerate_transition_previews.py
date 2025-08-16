#!/usr/bin/env python3
"""
Regenerate transition preview GIFs using two static images.
Creates 64x64 pixel preview GIFs for each transition defined in transitions.json.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

def get_project_root():
    """Find the project root directory."""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / 'resources').exists():
            return current
        current = current.parent
    return Path.cwd()

# FFmpeg transition commands mapping
TRANSITION_MAP = {
    # Basic transitions
    "fade": "xfade=transition=fade:duration=1:offset=0.5",
    "fadeblack": "xfade=transition=fadeblack:duration=1:offset=0.5",
    "fadewhite": "xfade=transition=fadewhite:duration=1:offset=0.5",
    "fadegrays": "xfade=transition=fadegrays:duration=1:offset=0.5",
    "dissolve": "xfade=transition=dissolve:duration=1:offset=0.5",
    
    # Wipe transitions
    "wipeleft": "xfade=transition=wipeleft:duration=1:offset=0.5",
    "wiperight": "xfade=transition=wiperight:duration=1:offset=0.5",
    "wipeup": "xfade=transition=wipeup:duration=1:offset=0.5",
    "wipedown": "xfade=transition=wipedown:duration=1:offset=0.5",
    "wipetl": "xfade=transition=wipetl:duration=1:offset=0.5",
    "wipetr": "xfade=transition=wipetr:duration=1:offset=0.5",
    "wipebl": "xfade=transition=wipebl:duration=1:offset=0.5",
    "wipebr": "xfade=transition=wipebr:duration=1:offset=0.5",
    
    # Slide transitions
    "slideleft": "xfade=transition=slideleft:duration=1:offset=0.5",
    "slideright": "xfade=transition=slideright:duration=1:offset=0.5",
    "slideup": "xfade=transition=slideup:duration=1:offset=0.5",
    "slidedown": "xfade=transition=slidedown:duration=1:offset=0.5",
    
    # Smooth transitions
    "smoothleft": "xfade=transition=smoothleft:duration=1:offset=0.5",
    "smoothright": "xfade=transition=smoothright:duration=1:offset=0.5",
    "smoothup": "xfade=transition=smoothup:duration=1:offset=0.5",
    "smoothdown": "xfade=transition=smoothdown:duration=1:offset=0.5",
    
    # Cover transitions
    "coverleft": "xfade=transition=coverleft:duration=1:offset=0.5",
    "coverright": "xfade=transition=coverright:duration=1:offset=0.5",
    "coverup": "xfade=transition=coverup:duration=1:offset=0.5",
    "coverdown": "xfade=transition=coverdown:duration=1:offset=0.5",
    
    # Reveal transitions
    "revealleft": "xfade=transition=revealleft:duration=1:offset=0.5",
    "revealright": "xfade=transition=revealright:duration=1:offset=0.5",
    "revealup": "xfade=transition=revealup:duration=1:offset=0.5",
    "revealdown": "xfade=transition=revealdown:duration=1:offset=0.5",
    
    # Geometric transitions
    "circleopen": "xfade=transition=circleopen:duration=1:offset=0.5",
    "circleclose": "xfade=transition=circleclose:duration=1:offset=0.5",
    "circlecrop": "xfade=transition=circlecrop:duration=1:offset=0.5",
    "rectcrop": "xfade=transition=rectcrop:duration=1:offset=0.5",
    
    # Door transitions
    "horzopen": "xfade=transition=horzopen:duration=1:offset=0.5",
    "horzclose": "xfade=transition=horzclose:duration=1:offset=0.5",
    "vertopen": "xfade=transition=vertopen:duration=1:offset=0.5",
    "vertclose": "xfade=transition=vertclose:duration=1:offset=0.5",
    
    # Diagonal transitions
    "diagtl": "xfade=transition=diagtl:duration=1:offset=0.5",
    "diagtr": "xfade=transition=diagtr:duration=1:offset=0.5",
    "diagbl": "xfade=transition=diagbl:duration=1:offset=0.5",
    "diagbr": "xfade=transition=diagbr:duration=1:offset=0.5",
    
    # Slice transitions
    "hlslice": "xfade=transition=hlslice:duration=1:offset=0.5",
    "hrslice": "xfade=transition=hrslice:duration=1:offset=0.5",
    "vuslice": "xfade=transition=vuslice:duration=1:offset=0.5",
    "vdslice": "xfade=transition=vdslice:duration=1:offset=0.5",
    
    # Special transitions
    "radial": "xfade=transition=radial:duration=1:offset=0.5",
    "zoomin": "xfade=transition=zoomin:duration=1:offset=0.5",
    "pixelize": "xfade=transition=pixelize:duration=1:offset=0.5",
    "distance": "xfade=transition=distance:duration=1:offset=0.5",
    "squeezev": "xfade=transition=squeezev:duration=1:offset=0.5",
    "squeezeh": "xfade=transition=squeezeh:duration=1:offset=0.5",
}

def create_transition_preview(transition_id, transition_name, img1_path, img2_path, output_path):
    """Create a transition preview GIF using FFmpeg."""
    
    if transition_id not in TRANSITION_MAP:
        print(f"⚠️  No mapping for transition '{transition_id}', skipping...")
        return False
    
    transition_filter = TRANSITION_MAP[transition_id]
    
    # FFmpeg command to create transition between two images
    cmd = [
        'ffmpeg', '-y',  # Overwrite output files
        '-loop', '1', '-t', '1.5', '-i', str(img1_path),  # First image for 1.5 seconds
        '-loop', '1', '-t', '1.5', '-i', str(img2_path),  # Second image for 1.5 seconds
        '-filter_complex', 
        f'[0:v]scale=64:64[v0];[1:v]scale=64:64[v1];[v0][v1]{transition_filter}[out]',
        '-map', '[out]',
        '-r', '10',  # 10 FPS for GIF
        '-t', '2',   # Total duration 2 seconds
        str(output_path)
    ]
    
    try:
        print(f"🎬 Generating {transition_name} ({transition_id})...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Generated: {output_path}")
            return True
        else:
            print(f"❌ Failed to generate {transition_id}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout generating {transition_id}")
        return False
    except Exception as e:
        print(f"💥 Error generating {transition_id}: {e}")
        return False

def main():
    """Main function to generate all transition previews."""
    print("🎭 Starting transition preview generation...")
    
    # Setup paths
    project_root = get_project_root()
    transitions_file = project_root / 'resources' / 'transitions.json'
    preview_cache_dir = project_root / 'resources' / 'preview_cache'
    
    # Input images - look in main resources directory
    img1_path = project_root / 'resources' / 'preview-a.jpg'
    img2_path = project_root / 'resources' / 'preview-b.jpg'
    
    # Verify files exist
    if not transitions_file.exists():
        print(f"❌ Transitions file not found: {transitions_file}")
        return
        
    if not img1_path.exists():
        print(f"❌ First image not found: {img1_path}")
        return
        
    if not img2_path.exists():
        print(f"❌ Second image not found: {img2_path}")
        return
    
    # Create preview cache directory
    preview_cache_dir.mkdir(exist_ok=True)
    
    # Load transitions
    try:
        with open(transitions_file, 'r', encoding='utf-8') as f:
            transitions = json.load(f)
    except Exception as e:
        print(f"❌ Error loading transitions: {e}")
        return
    
    print(f"📁 Found {len(transitions)} transitions to process")
    print(f"🖼️  Using images: {img1_path.name} → {img2_path.name}")
    
    # Process each transition
    generated = 0
    failed = 0
    skipped = 0
    
    for transition in transitions:
        transition_id = transition['id']
        transition_name = transition['name']
        output_path = preview_cache_dir / f"transition_{transition_id}.gif"
        
        # Skip if file already exists (optional)
        if output_path.exists():
            print(f"⏭️  Skipping {transition_name} (already exists)")
            skipped += 1
            continue
        
        success = create_transition_preview(
            transition_id, 
            transition_name, 
            img1_path, 
            img2_path, 
            output_path
        )
        
        if success:
            generated += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"✅ Generated: {generated}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📝 Total: {len(transitions)}")
    
    if failed > 0:
        print(f"\n⚠️  {failed} transitions failed. Check FFmpeg installation and xfade filter support.")

if __name__ == '__main__':
    main() 
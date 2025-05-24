#!/usr/bin/env python3
"""
Simple RTSP to YouTube Live Streaming Tool

This script streams video from a TP-Link Tapo C121 camera (via RTSP) to YouTube Live.
It uses FFmpeg for a simple, reliable streaming solution.

Usage:
  python main.py

Edit the CAMERA_URL and YOUTUBE_KEY variables below before running.

Author: gdeckard
Last Updated: 2025
"""

import os
import sys
import time
import signal
import subprocess

# ========== EDIT THESE VALUES ==========
# Your camera's RTSP URL (default for TP-Link Tapo C121)
CAMERA_URL = "rtsp://username:password@camera-ip:554/stream1"

# Your YouTube Stream Key from YouTube Studio -> Go Live -> Stream
YOUTUBE_KEY = "your-stream-key-here"

# YouTube RTMP URL (don't change unless YouTube changes their endpoint)
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_KEY}"
# ======================================

def check_dependencies():
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: FFmpeg is not installed or not in the PATH.")
        print("Please install FFmpeg: https://ffmpeg.org/download.html")
        return False

def start_stream():
    """Start streaming from camera to YouTube."""
    # Print header
    print("=" * 50)
    print("TP-Link Tapo C121 to YouTube Live Stream")
    print("=" * 50)
    print(f"Camera URL: {CAMERA_URL}")
    print(f"Streaming to: YouTube Live")
    print("Press Ctrl+C to stop streaming")
    print("=" * 50)
    
    # Build the FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",          # Use TCP (more reliable than UDP)
        "-i", CAMERA_URL,                  # Input from RTSP stream
        
        # Video encoding settings
        "-c:v", "libx264",                 # Use H.264 codec
        "-preset", "ultrafast",            # Fastest encoding
        "-tune", "zerolatency",            # Minimize latency
        "-b:v", "2000k",                   # Video bitrate
        "-pix_fmt", "yuv420p",             # Required for compatibility
        
        # Audio settings
        "-c:a", "aac",                     # AAC audio codec
        "-b:a", "128k",                    # Audio bitrate
        
        # Output settings
        "-f", "flv",                       # FLV format for RTMP
        YOUTUBE_URL                        # YouTube stream URL
    ]
    
    # Set up signal handler for clean exit
    def signal_handler(sig, frame):
        print("\nStopping stream (Ctrl+C detected)...")
        if process and process.poll() is None:
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Launch FFmpeg process
    print("Starting streaming process...")
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print(f"Stream started with PID: {process.pid}")
    
    try:
        # Monitor process and print FFmpeg output
        for line in process.stderr:
            if "error" in line.lower() or "warning" in line.lower():
                print(f"FFmpeg: {line.strip()}")
            elif "speed" in line and "bitrate" in line:
                print(f"Status: {line.strip()}")
    
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    
    return process.poll()

if __name__ == "__main__":
    # Validate the YouTube stream key
    if YOUTUBE_KEY == "your-stream-key-here":
        print("ERROR: Please edit this script to set your YouTube Stream Key.")
        print("1. Open main.py in a text editor")
        print("2. Find the YOUTUBE_KEY variable near the top")
        print("3. Replace 'your-stream-key-here' with your actual key from YouTube Studio")
        sys.exit(1)
    
    # Validate the camera URL
    if "username:password" in CAMERA_URL:
        print("ERROR: Please edit this script to set your camera's RTSP URL.")
        print("1. Open main.py in a text editor")
        print("2. Find the CAMERA_URL variable near the top")
        print("3. Replace username and password with your actual camera credentials")
        sys.exit(1)
    
    # Check if FFmpeg is available
    if not check_dependencies():
        sys.exit(1)
    
    # Start streaming
    try:
        exit_code = start_stream()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

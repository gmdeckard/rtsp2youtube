#!/usr/bin/env python3
"""
Streamlink to YouTube Live Streaming Tool

This script streams video from a TP-Link Tapo C121 camera to YouTube Live.
It uses Streamlink and FFmpeg for an alternative streaming approach.

Usage:
  python streamlink_version.py

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
# Your camera's URL or IP address
CAMERA_URL = "http://192.168.0.191/"     # Web interface URL

# Your camera login credentials
CAMERA_USER = "username"
CAMERA_PASS = "password"

# Your YouTube Stream Key from YouTube Studio -> Go Live -> Stream
YOUTUBE_KEY = "your-stream-key-here"

# YouTube RTMP URL (don't change unless YouTube changes their endpoint)
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_KEY}"
# ======================================

def check_dependencies():
    """Check if Streamlink and FFmpeg are installed."""
    missing = []
    
    try:
        subprocess.run(["streamlink", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        missing.append("streamlink")
        
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        missing.append("ffmpeg")
        
    if missing:
        print(f"Error: The following dependencies are missing: {', '.join(missing)}")
        print("Please install them:")
        if "streamlink" in missing:
            print("  pip install streamlink")
        if "ffmpeg" in missing:
            print("  https://ffmpeg.org/download.html")
        return False
        
    return True

def start_stream():
    """Start streaming from camera to YouTube using Streamlink and FFmpeg."""
    # Print header
    print("=" * 50)
    print("TP-Link Tapo C121 to YouTube Live Stream (Streamlink)")
    print("=" * 50)
    print(f"Camera URL: {CAMERA_URL}")
    print(f"Streaming to: YouTube Live")
    print("Press Ctrl+C to stop streaming")
    print("=" * 50)
    
    # Streamlink command to get the HLS stream from the camera
    streamlink_cmd = [
        "streamlink",
        "--player-external-http",
        "--player", "ffmpeg",
        "--player-args",
        (f'-i - -c:v libx264 -preset ultrafast -tune zerolatency -b:v 2000k '
         f'-pix_fmt yuv420p -c:a aac -b:a 128k -f flv "{YOUTUBE_URL}"'),
        f"{CAMERA_URL}",
        "best",
        "--http-header", "Referer=http://192.168.0.191/",
        "--http-header", f"Authorization=Basic {CAMERA_USER}:{CAMERA_PASS}"
    ]
    
    # Set up signal handler for clean exit
    process = None
    
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
    
    # Launch Streamlink process
    print("Starting streaming process...")
    process = subprocess.Popen(
        streamlink_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print(f"Stream started with PID: {process.pid}")
    
    try:
        # Monitor process and print output
        for line in process.stderr:
            if "error" in line.lower() or "warning" in line.lower():
                print(f"Error: {line.strip()}")
            else:
                print(f"Status: {line.strip()}")
    
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    
    return process.poll()

if __name__ == "__main__":
    # Validate the YouTube stream key
    if YOUTUBE_KEY == "your-stream-key-here":
        print("ERROR: Please edit this script to set your YouTube Stream Key.")
        print("1. Open streamlink_version.py in a text editor")
        print("2. Find the YOUTUBE_KEY variable near the top")
        print("3. Replace 'your-stream-key-here' with your actual key from YouTube Studio")
        sys.exit(1)
    
    # Validate the camera credentials
    if CAMERA_USER == "username" or CAMERA_PASS == "password":
        print("ERROR: Please edit this script to set your camera's login credentials.")
        print("1. Open streamlink_version.py in a text editor")
        print("2. Find the CAMERA_USER and CAMERA_PASS variables near the top")
        print("3. Replace them with your actual camera login details")
        sys.exit(1)
    
    # Check if dependencies are available
    if not check_dependencies():
        sys.exit(1)
    
    # Start streaming
    try:
        exit_code = start_stream()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Multi-Camera RTSP to YouTube Live Streaming Tool

This script streams video from multiple TP-Link Tapo C121 cameras (via RTSP) 
to multiple YouTube Live streams simultaneously.
It uses FFmpeg for simple, reliable streaming.

Usage:
  python multi_stream.py

Edit the CAMERA_CONFIG list below before running.

Author: gmdeckard
Last Updated: 2025-05-24
"""

import os
import sys
import time
import signal
import subprocess
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("stream_log.txt")
    ]
)
logger = logging.getLogger("MultiStream")

# ========== EDIT THESE VALUES ==========
# List of camera configurations
# Each entry should be a dictionary with:
# - name: A friendly name for the camera
# - rtsp_url: The RTSP URL for the camera
# - youtube_key: The YouTube Stream Key for this stream
# - quality: Video quality settings (optional, see examples)

CAMERA_CONFIG = [
    {
        "name": "Front Door",
        "rtsp_url": "rtsp://username:password@camera-ip:554/stream1",
        "youtube_key": "your-stream-key-here",
        # Optional quality settings - if not specified, defaults will be used
        "quality": {
            "resolution": "1280x720",
            "bitrate": "2000k",
        }
    },
    # Add more cameras as needed following the same format
    {
        "name": "Back Yard",
        "rtsp_url": "rtsp://username:password@camera-ip:554/stream1",
        "youtube_key": "your-stream-key-here",
    },
    # Example with more detailed quality settings
    # {
    #     "name": "Living Room",
    #     "rtsp_url": "rtsp://username:password@camera-ip:554/stream1",
    #     "youtube_key": "your-stream-key-here",
    #     "quality": {
    #         "resolution": "1920x1080",
    #         "bitrate": "3000k",
    #         "framerate": "30",
    #         "audio_bitrate": "128k",
    #     }
    # },
]
# ======================================

# Default quality settings
DEFAULT_QUALITY = {
    "resolution": "1280x720",
    "bitrate": "2000k",
    "framerate": "25",
    "audio_bitrate": "128k",
    "preset": "ultrafast",
}

# Global dictionary to keep track of all processes
stream_processes = {}
stop_event = threading.Event()

def check_dependencies():
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Error: FFmpeg is not installed or not in the PATH.")
        logger.error("Please install FFmpeg: https://ffmpeg.org/download.html")
        return False

def build_ffmpeg_command(camera_config):
    """Build the FFmpeg command for a specific camera configuration."""
    # Get quality settings, using defaults if not specified
    quality = DEFAULT_QUALITY.copy()
    if "quality" in camera_config:
        quality.update(camera_config["quality"])
    
    # YouTube RTMP URL
    youtube_url = f"rtmp://a.rtmp.youtube.com/live2/{camera_config['youtube_key']}"
    
    # Build the FFmpeg command
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",         # Use TCP (more reliable than UDP)
        "-i", camera_config["rtsp_url"],  # Input from RTSP stream
        
        # Video encoding settings
        "-c:v", "libx264",                # Use H.264 codec
        "-preset", quality["preset"],     # Encoding preset
        "-tune", "zerolatency",           # Minimize latency
        "-b:v", quality["bitrate"],       # Video bitrate
        "-r", quality["framerate"],       # Frame rate
        "-s", quality["resolution"],      # Resolution
        "-pix_fmt", "yuv420p",            # Required for compatibility
        
        # Audio settings
        "-c:a", "aac",                    # AAC audio codec
        "-b:a", quality["audio_bitrate"], # Audio bitrate
        
        # Output settings
        "-f", "flv",                      # FLV format for RTMP
        youtube_url                       # YouTube stream URL
    ]
    
    return cmd

def stream_camera(camera_config):
    """Stream a single camera to YouTube in its own thread."""
    camera_name = camera_config["name"]
    logger.info(f"Starting stream for camera: {camera_name}")
    
    # Build the FFmpeg command
    ffmpeg_cmd = build_ffmpeg_command(camera_config)
    
    # Create a unique logger for this camera
    cam_logger = logging.getLogger(f"Camera.{camera_name}")
    
    try:
        # Launch FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Store the process
        stream_processes[camera_name] = process
        
        cam_logger.info(f"Stream started with PID: {process.pid}")
        
        # Monitor process output
        while process.poll() is None and not stop_event.is_set():
            line = process.stderr.readline().strip()
            if not line:
                continue
                
            # Log important information
            lower_line = line.lower()
            if "error" in lower_line:
                cam_logger.error(f"FFmpeg Error: {line}")
            elif "warning" in lower_line:
                cam_logger.warning(f"FFmpeg Warning: {line}")
            elif "speed" in line and "bitrate" in line:
                cam_logger.info(f"Status: {line}")
        
        # Check why the process ended
        if stop_event.is_set():
            cam_logger.info(f"Stream manually stopped for camera: {camera_name}")
        else:
            cam_logger.warning(f"Stream ended unexpectedly for camera: {camera_name} with return code {process.returncode}")
    
    except Exception as e:
        cam_logger.error(f"Error in stream for camera {camera_name}: {str(e)}")
    
    finally:
        # Remove process from the tracking dictionary
        if camera_name in stream_processes:
            del stream_processes[camera_name]

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals."""
    logger.info("Stopping all streams... (Ctrl+C detected)")
    stop_event.set()
    
    # Terminate all FFmpeg processes
    for name, process in list(stream_processes.items()):
        if process and process.poll() is None:
            logger.info(f"Terminating stream for camera: {name}")
            try:
                process.terminate()
                # Wait a bit to see if it terminates gracefully
                time.sleep(2)
                if process.poll() is None:
                    # Force kill if still running
                    process.kill()
            except Exception as e:
                logger.error(f"Error terminating process for {name}: {e}")
    
    sys.exit(0)

def validate_config():
    """Validate the camera configurations before starting streams."""
    if not CAMERA_CONFIG:
        logger.error("ERROR: No camera configurations found!")
        logger.error("Please edit the script to add at least one camera configuration.")
        return False
    
    valid = True
    for i, config in enumerate(CAMERA_CONFIG):
        # Check required fields
        if "name" not in config:
            logger.error(f"Camera #{i+1} is missing a name!")
            valid = False
        
        if "rtsp_url" not in config or not config["rtsp_url"].startswith("rtsp://"):
            logger.error(f"Camera '{config.get('name', f'#{i+1}')}' has an invalid RTSP URL!")
            valid = False
        
        if "youtube_key" not in config or config["youtube_key"] == "your-stream-key-here":
            logger.error(f"Camera '{config.get('name', f'#{i+1}')}' has an invalid YouTube stream key!")
            valid = False
    
    return valid

def main():
    """Main function to start all camera streams."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if FFmpeg is installed
    if not check_dependencies():
        sys.exit(1)
    
    # Validate configurations
    if not validate_config():
        logger.error("Please correct the configuration errors and try again.")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("Multi-Camera RTSP to YouTube Live Stream")
    logger.info("=" * 50)
    logger.info(f"Starting {len(CAMERA_CONFIG)} camera streams")
    logger.info("Press Ctrl+C to stop all streams")
    logger.info("=" * 50)
    
    # Create threads for each camera
    threads = []
    for config in CAMERA_CONFIG:
        thread = threading.Thread(target=stream_camera, args=(config,))
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete (or until interrupted)
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()

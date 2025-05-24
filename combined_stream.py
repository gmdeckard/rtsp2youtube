#!/usr/bin/env python3
"""
Combined-Camera RTSP to YouTube Live Streaming Tool

This script combines video from multiple TP-Link Tapo C121 cameras (via RTSP)
into a single YouTube Live stream with either side-by-side layout or automatic
switching between cameras.

Usage:
  python combined_stream.py

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
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("combined_stream_log.txt")
    ]
)
logger = logging.getLogger("CombinedStream")

# ========== EDIT THESE VALUES ==========
# List of camera configurations
# Each entry should be a dictionary with:
# - name: A friendly name for the camera
# - rtsp_url: The RTSP URL for the camera

CAMERA_CONFIG = [
    {
        "name": "Camera 1",
        "rtsp_url": "rtsp://username:password@camera1-ip:554/stream1",
    },
    {
        "name": "Camera 2",
        "rtsp_url": "rtsp://username:password@camera2-ip:554/stream1",
    },
    # Add more cameras as needed following the same format
]

# Your YouTube Stream Key from YouTube Studio -> Go Live -> Stream
YOUTUBE_KEY = "your-stream-key-here"

# Layout configuration
LAYOUT = "side-by-side"  # Options: "side-by-side", "grid", "switch"
SWITCH_INTERVAL = 10  # Seconds between camera switches (only if LAYOUT="switch")

# Quality settings
QUALITY = {
    "resolution": "1280x720",
    "bitrate": "3000k",
    "framerate": "25",
    "audio_bitrate": "128k",
    "preset": "ultrafast",
}
# ======================================

# YouTube RTMP URL
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_KEY}"

# Global process variable
stream_process = None
stop_event = threading.Event()

def check_dependencies():
    """Check if FFmpeg is installed with required capabilities."""
    try:
        # Check if FFmpeg is installed
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.info(f"FFmpeg installed: {result.stdout.splitlines()[0]}")
        
        # Check if FFmpeg has the filter_complex capabilities (needed for combining streams)
        # This is a basic check, most modern FFmpeg installations have these capabilities
        cmd = ["ffmpeg", "-filters"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if "overlay" not in result.stdout or "hstack" not in result.stdout:
            logger.warning("FFmpeg might not have all required filters. Complex layouts might not work.")
            
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Error: FFmpeg is not installed or not in the PATH.")
        logger.error("Please install FFmpeg: https://ffmpeg.org/download.html")
        return False

def validate_config():
    """Validate the camera configuration."""
    if not CAMERA_CONFIG:
        logger.error("Error: No cameras configured. Please add camera configurations.")
        return False
        
    if len(CAMERA_CONFIG) < 2:
        logger.error("Error: At least two cameras are required for combined streaming.")
        return False
        
    if YOUTUBE_KEY == "your-stream-key-here":
        logger.error("Error: Please edit this script to set your YouTube Stream Key.")
        return False
        
    for idx, camera in enumerate(CAMERA_CONFIG):
        if "rtsp_url" not in camera or not camera["rtsp_url"] or camera["rtsp_url"].startswith("rtsp://username:password"):
            logger.error(f"Error: Camera {idx+1} ({camera.get('name', 'Unknown')}) has an invalid RTSP URL.")
            return False
            
    return True

def build_ffmpeg_command():
    """Build the FFmpeg command to combine camera streams."""
    cmd = ["ffmpeg"]
    
    # Input streams
    for i, camera in enumerate(CAMERA_CONFIG):
        cmd.extend(["-rtsp_transport", "tcp", "-i", camera["rtsp_url"]])
    
    # Add complex filter based on layout
    filter_complex = build_filter_complex()
    cmd.extend(["-filter_complex", filter_complex])
    
    # Output settings
    cmd.extend([
        "-map", "[outv]",     # Use the output video from the filter complex
        "-map", "0:a",        # Use audio from the first input (if available)
        "-c:v", "libx264",    # Video codec
        "-preset", QUALITY["preset"],
        "-tune", "zerolatency",
        "-b:v", QUALITY["bitrate"],
        "-r", QUALITY["framerate"],
        "-g", str(int(float(QUALITY["framerate"]) * 2)),  # GOP size
        "-keyint_min", str(int(float(QUALITY["framerate"]))),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", QUALITY["audio_bitrate"],
        "-f", "flv",
        YOUTUBE_URL
    ])
    
    return cmd

def build_filter_complex():
    """Build the filter complex string based on the selected layout."""
    num_cameras = len(CAMERA_CONFIG)
    
    if LAYOUT == "switch":
        # Create a switching layout using the overlay filter and enable timestamps
        # For n inputs, we create n-1 overlays that switch between sources
        filters = []
        for i in range(num_cameras):
            # Scale each input to the target resolution
            filters.append(f"[{i}:v]scale={QUALITY['resolution']},setpts=PTS-STARTPTS[v{i}]")
        
        # Create a switching mechanism
        switch_expr = ""
        for i in range(num_cameras):
            if i > 0:
                switch_expr += "+"
            start_time = i * SWITCH_INTERVAL
            end_time = (i+1) * SWITCH_INTERVAL
            # This creates a loop by using the modulo of the timestamp
            switch_expr += f"if(mod(t,{num_cameras*SWITCH_INTERVAL})<={end_time}*gte(mod(t,{num_cameras*SWITCH_INTERVAL}),{start_time}),1,0)"
        
        for i in range(num_cameras):
            filters.append(f"[v{i}]split=1[v{i}out]")
        
        # Build the chain of overlays
        filter_chain = f"[v0out]"
        for i in range(1, num_cameras):
            filter_chain += f"[v{i}out]overlay=shortest=1:enable='{switch_expr}',"
            if i < num_cameras - 1:
                filter_chain += f"[tmp{i}];[tmp{i}]"
        filter_chain += "[outv]"
        
        return ";".join(filters) + ";" + filter_chain
        
    elif LAYOUT == "grid":
        # Create a grid layout (2x2 or similar)
        filters = []
        
        # Determine grid dimensions (roughly square)
        import math
        grid_size = math.ceil(math.sqrt(num_cameras))
        rows = grid_size
        cols = (num_cameras + rows - 1) // rows
        cell_width = int(int(QUALITY["resolution"].split("x")[0]) / cols)
        cell_height = int(int(QUALITY["resolution"].split("x")[1]) / rows)
        
        # Scale each input to the appropriate cell size
        for i in range(num_cameras):
            filters.append(f"[{i}:v]scale={cell_width}:{cell_height}[v{i}]")
        
        # Build the grid using the xstack filter
        xstack_filter = "xstack=inputs=" + str(num_cameras) + ":layout="
        for i in range(num_cameras):
            row = i // cols
            col = i % cols
            xstack_filter += f"{col}_{row}"
            if i < num_cameras - 1:
                xstack_filter += "|"
        
        # Combine scaled inputs
        input_list = "".join(f"[v{i}]" for i in range(num_cameras))
        filters.append(f"{input_list}{xstack_filter}[outv]")
        
        return ";".join(filters)
        
    else:  # Default: side-by-side
        # Create a side-by-side layout
        filters = []
        scaled_width = int(int(QUALITY["resolution"].split("x")[0]) / num_cameras)
        full_height = int(QUALITY["resolution"].split("x")[1])
        
        # Scale each input
        for i in range(num_cameras):
            filters.append(f"[{i}:v]scale={scaled_width}:{full_height}[v{i}]")
        
        # Use hstack to place them side by side
        input_list = "".join(f"[v{i}]" for i in range(num_cameras))
        filters.append(f"{input_list}hstack=inputs={num_cameras}[outv]")
        
        return ";".join(filters)

def start_streaming():
    """Start streaming with the combined camera feeds."""
    global stream_process
    
    # Print header
    logger.info("=" * 50)
    logger.info("Multiple Camera Combined Stream to YouTube Live")
    logger.info("=" * 50)
    logger.info(f"Layout: {LAYOUT}")
    if LAYOUT == "switch":
        logger.info(f"Switching interval: {SWITCH_INTERVAL} seconds")
    logger.info(f"Cameras: {', '.join(camera.get('name', f'Camera {i+1}') for i, camera in enumerate(CAMERA_CONFIG))}")
    logger.info(f"Streaming to: YouTube Live")
    logger.info("Press Ctrl+C to stop streaming")
    logger.info("=" * 50)
    
    # Build and execute the FFmpeg command
    cmd = build_ffmpeg_command()
    logger.info(f"Command: {' '.join(cmd)}")
    
    def signal_handler(sig, frame):
        logger.info("\nStopping stream (Ctrl+C detected)...")
        stop_streaming()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting streaming process...")
        stream_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            text=True
        )
        
        logger.info(f"Stream started with PID: {stream_process.pid}")
        
        # Monitor process and print output
        for line in stream_process.stderr:
            if stop_event.is_set():
                break
                
            if "error" in line.lower():
                logger.error(f"FFmpeg: {line.strip()}")
            elif "warning" in line.lower():
                logger.warning(f"FFmpeg: {line.strip()}")
            else:
                logger.info(f"FFmpeg: {line.strip()}")
                
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    
    return stream_process.poll()

def stop_streaming():
    """Stop the streaming process."""
    global stream_process
    
    if stream_process and stream_process.poll() is None:
        logger.info("Terminating FFmpeg process...")
        stop_event.set()
        
        # Try to send a quit signal to FFmpeg first (more graceful than terminate)
        try:
            stream_process.communicate(input="q", timeout=3)
        except (subprocess.TimeoutExpired, BrokenPipeError):
            pass
            
        # If it's still running, try to terminate
        if stream_process.poll() is None:
            stream_process.terminate()
            time.sleep(1)
            
            # If still running, force kill
            if stream_process.poll() is None:
                stream_process.kill()
                
        logger.info("Streaming stopped")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Combined Camera Stream to YouTube Live')
    parser.add_argument('--layout', choices=['side-by-side', 'grid', 'switch'],
                        default=LAYOUT, help='Layout type for combining streams')
    parser.add_argument('--switch-interval', type=int, default=SWITCH_INTERVAL,
                        help='Interval in seconds between camera switches (for switch layout)')
    args = parser.parse_args()
    
    # Update global variables based on args
    global LAYOUT, SWITCH_INTERVAL
    LAYOUT = args.layout
    SWITCH_INTERVAL = args.switch_interval

if __name__ == "__main__":
    # Parse command line arguments
    parse_arguments()
    
    # Validate YouTube key and camera configurations
    if not validate_config():
        sys.exit(1)
    
    # Check if FFmpeg is available
    if not check_dependencies():
        sys.exit(1)
    
    # Start streaming
    try:
        exit_code = start_streaming()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Error: {e}")
        stop_streaming()
        sys.exit(1)

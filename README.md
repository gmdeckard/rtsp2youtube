# TP-Link Tapo C121 to YouTube Live Streaming

Simple scripts to stream video from a TP-Link Tapo C121 camera to YouTube Live.

This repository contains three different approaches:

1. **Single Camera Stream** - Stream one camera to YouTube Live (`main.py`)
2. **Multiple Camera Streams** - Stream multiple cameras simultaneously (`multi_stream.py`)
3. **Streamlink Method** - Alternative method using Streamlink (`streamlink_version.py`)

## Option 1: Direct RTSP Streaming (Recommended)

The `main.py` script uses FFmpeg to directly capture the RTSP stream from your camera and push it to YouTube Live.

### Usage

1. Edit `main.py` and update:
   - `CAMERA_URL` with your camera's RTSP URL
   - `YOUTUBE_KEY` with your YouTube Stream Key

2. Run the script:
   ```bash
   python main.py
   ```

## Option 2: Multiple Camera Streams

The `multi_stream.py` script allows you to stream multiple cameras to multiple YouTube Live streams simultaneously, each in its own thread.

### Usage

1. Edit `multi_stream.py` and update the `CAMERA_CONFIG` list:
   ```python
   CAMERA_CONFIG = [
       {
           "name": "Front Door",
           "rtsp_url": "rtsp://username:password@camera-ip:554/stream1",
           "youtube_key": "your-stream-key-here",
           "quality": {
               "resolution": "1280x720",
               "bitrate": "2000k",
           }
       },
       # Add more cameras as needed
   ]
   ```

2. Run the script:
   ```bash
   python multi_stream.py
   ```

## Option 3: Streamlink Method (Alternative)

The `streamlink_version.py` script uses Streamlink and FFmpeg as an alternative method, which might work better in some scenarios.

### Usage

1. Install Streamlink if not already installed:
   ```bash
   pip install streamlink
   ```

2. Edit `streamlink_version.py` and update:
   - `CAMERA_URL` with your camera's web interface URL
   - `CAMERA_USER` and `CAMERA_PASS` with your login credentials
   - `YOUTUBE_KEY` with your YouTube Stream Key

3. Run the script:
   ```bash
   python streamlink_version.py
   ```

## Requirements

- Python 3.6+
- FFmpeg must be installed on your system
- For option 2: Streamlink
- A YouTube account with Live Streaming enabled
- An IP camera that provides RTSP streams (tested with TP-Link Tapo C121)

## Camera RTSP URL Format

Typical RTSP URL format for TP-Link Tapo C121 cameras:
```
rtsp://username:password@192.168.0.191:554/stream1
```

## YouTube Stream Key

Get your stream key from YouTube Studio:
1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click "Go Live" in the top-right corner
3. Copy your Stream Key from the Stream settings

## Installation

1. Ensure FFmpeg is installed:

   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # macOS with Homebrew
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

2. For the alternative method, install Streamlink:

   ```bash
   # With pip
   pip install streamlink
   
   # Ubuntu/Debian
   sudo apt install streamlink
   ```

## Troubleshooting

### Camera Connection Issues
- Make sure your camera is on the same network as your computer
- Verify your camera credentials
- Try accessing the RTSP URL directly with VLC media player

### Streaming Issues
- Check that your YouTube account has live streaming enabled
- Ensure your stream key is correct and hasn't expired
- Monitor your network bandwidth - streaming requires a stable connection
- If direct RTSP doesn't work, try the Streamlink version

### FFmpeg Command Customization

The script uses basic FFmpeg parameters for simplicity. You can modify the FFmpeg command in the script to adjust:
- Video quality (bitrate, resolution)
- Audio settings
- Latency and buffering

## License

MIT

## Acknowledgments

- FFmpeg team for their excellent media processing tool
- TP-Link for the Tapo camera RTSP implementation
- Streamlink project for the alternative streaming method

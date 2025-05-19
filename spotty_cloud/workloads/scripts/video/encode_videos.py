#!/usr/bin/env python
# Video encoding batch processing script

import os
import argparse
import glob
import subprocess
import logging
import concurrent.futures
import urllib.request
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('encoding.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('video_encoder')

# Define resolution presets
RESOLUTION_PRESETS = {
    '4k': {'width': 3840, 'height': 2160, 'bitrate': '15M'},
    '1080p': {'width': 1920, 'height': 1080, 'bitrate': '8M'},
    '720p': {'width': 1280, 'height': 720, 'bitrate': '5M'},
    '480p': {'width': 854, 'height': 480, 'bitrate': '2.5M'},
    '360p': {'width': 640, 'height': 360, 'bitrate': '1M'},
    '240p': {'width': 426, 'height': 240, 'bitrate': '700K'}
}

# Define sample videos with name, URL, and approximate size
SAMPLE_VIDEOS = {
    'big_buck_bunny_720p': {
        'url': 'https://download.blender.org/peach/bigbuckbunny_movies/big_buck_bunny_720p_surround.avi',
        'size_mb': 184,
        'description': 'Big Buck Bunny 720p (Blender Foundation)'
    },
    'tears_of_steel_1080p': {
        'url': 'https://download.blender.org/tears/tears_of_steel_1080p.mov',
        'size_mb': 788,
        'description': 'Tears of Steel 1080p (Blender Foundation)'
    },
    'sintel_trailer_2k': {
        'url': 'https://download.blender.org/durian/trailer/sintel_trailer-2k.mp4',
        'size_mb': 80,
        'description': 'Sintel Trailer 2K (Blender Foundation)'
    }
}

# Progress bar for download
class DownloadProgressBar:
    def __init__(self, total_size):
        self.total_size = total_size
        self.downloaded = 0
        self.prev_percent = 0

    def update(self, count):
        self.downloaded += count
        percent = int(self.downloaded * 100 / self.total_size) if self.total_size else 0
        if percent > self.prev_percent:
            self.prev_percent = percent
            chars = int(percent / 2)
            progress_bar = f"[{'#' * chars}{' ' * (50 - chars)}] {percent}%"
            print(f"\r{progress_bar}", end='', flush=True)

# Download a file with progress bar
def download_file(url, output_path):
    try:
        print(f"\nDownloading from {url}")
        print(f"Saving to {output_path}")
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Start the download with a progress bar
        with urllib.request.urlopen(url) as response:
            file_size = int(response.info().get('Content-Length', 0))
            progress_bar = DownloadProgressBar(file_size)
            
            with open(output_path, 'wb') as out_file:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    progress_bar.update(len(chunk))
            
            print("\nDownload complete!")
            return True
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return False

# Download a sample video if needed
def download_sample_video(sample_name, output_dir):
    if sample_name not in SAMPLE_VIDEOS:
        logger.error(f"Unknown sample video: {sample_name}")
        print(f"Available samples: {', '.join(SAMPLE_VIDEOS.keys())}")
        return None
        
    sample = SAMPLE_VIDEOS[sample_name]
    extension = sample['url'].split('.')[-1]
    output_path = os.path.join(output_dir, f"{sample_name}.{extension}")
    
    # Check if file already exists
    if os.path.exists(output_path):
        logger.info(f"Sample video already exists at {output_path}")
        return output_path
        
    # Download the file
    print(f"Downloading sample video: {sample['description']} (~{sample['size_mb']} MB)")
    if download_file(sample['url'], output_path):
        return output_path
    return None

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Batch video encoding tool')
    parser.add_argument('--input', type=str, default='/data/input', 
                        help='Input directory containing videos to encode')
    parser.add_argument('--output', type=str, default='/data/output',
                        help='Output directory for encoded videos')
    parser.add_argument('--formats', type=str, default='1080p,720p,480p,360p',
                        help='Comma-separated list of target resolutions')
    parser.add_argument('--extension', type=str, default='mp4',
                        help='File extension to search for (default: mp4)')
    parser.add_argument('--use_gpu', type=bool, default=False,
                        help='Use GPU acceleration for encoding')
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of parallel encoding workers')
    parser.add_argument('--crf', type=int, default=23,
                        help='Constant Rate Factor (quality setting, 0-51, lower is better)')
    parser.add_argument('--download_sample', type=str, default=None,
                        choices=list(SAMPLE_VIDEOS.keys()) + ['list'],
                        help='Download a sample video before encoding')
    parser.add_argument('--url', type=str, default=None,
                        help='URL to download a custom video')
    return parser.parse_args()

# Get video information using ffprobe
def get_video_info(video_path):
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,codec_name',
            '-of', 'json', video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"Error getting video info: {result.stderr}")
            return None
        
        import json
        info = json.loads(result.stdout)
        return info['streams'][0] if 'streams' in info and info['streams'] else None
    except Exception as e:
        logger.error(f"Exception getting video info: {str(e)}")
        return None

# Encode a single video to a specific resolution
def encode_video(input_path, output_path, resolution_key, resolution, use_gpu=False, crf=23):
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Build the ffmpeg command
        cmd = ['ffmpeg', '-i', input_path, '-y']
        
        # Add GPU acceleration if requested and available
        if use_gpu:
            cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
        
        # Add video encoding parameters
        cmd.extend([
            '-c:v', 'libx264' if not use_gpu else 'h264_nvenc',
            '-preset', 'slow' if not use_gpu else 'p4',
            '-crf', str(crf) if not use_gpu else '0',  # CRF for CPU, not used with GPU
            '-b:v', resolution['bitrate'],              # Target bitrate
            '-maxrate', resolution['bitrate'],          # Maximum bitrate
            '-bufsize', resolution['bitrate'],          # Buffer size
            '-vf', f"scale={resolution['width']}:{resolution['height']}",
            '-c:a', 'aac',                              # Audio codec
            '-b:a', '128k',                             # Audio bitrate
            '-movflags', '+faststart',                 # Web optimization
            output_path
        ])
        
        # Run the encoding process
        logger.info(f"Encoding {os.path.basename(input_path)} to {resolution_key}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        start_time = datetime.now()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        end_time = datetime.now()
        
        if result.returncode == 0:
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Successfully encoded {os.path.basename(input_path)} to {resolution_key} in {duration:.2f} seconds")
            return True
        else:
            logger.error(f"Error encoding {input_path} to {resolution_key}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Exception encoding {input_path} to {resolution_key}: {str(e)}")
        return False

# Process a single video file
def process_video(video_path, output_dir, formats, use_gpu, crf):
    try:
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        
        logger.info(f"Processing video: {video_filename}")
        
        # Get video information
        video_info = get_video_info(video_path)
        if not video_info:
            logger.error(f"Could not get information for {video_filename}, skipping")
            return False
        
        logger.info(f"Original video: {video_info.get('width')}x{video_info.get('height')}, codec: {video_info.get('codec_name')}")
        
        # Process each requested resolution
        success = True
        for format_key in formats:
            if format_key not in RESOLUTION_PRESETS:
                logger.warning(f"Unknown format {format_key}, skipping")
                continue
                
            resolution = RESOLUTION_PRESETS[format_key]
            output_file = os.path.join(output_dir, video_name, f"{video_name}_{format_key}.mp4")
            
            # Skip if the output already exists
            if os.path.exists(output_file):
                logger.info(f"Output file already exists: {output_file}, skipping")
                continue
                
            # Skip if requested resolution is higher than original
            if int(video_info.get('width', 0)) < resolution['width'] or int(video_info.get('height', 0)) < resolution['height']:
                logger.warning(f"Source resolution ({video_info.get('width')}x{video_info.get('height')}) is lower than requested {format_key}, skipping")
                continue
                
            # Encode to the target resolution
            if not encode_video(video_path, output_file, format_key, resolution, use_gpu, crf):
                success = False
        
        return success
    except Exception as e:
        logger.error(f"Error processing {video_path}: {str(e)}")
        return False

# Explanation of CPU vs GPU for video encoding
def print_encoding_guidance():
    print("\n==== CPU vs GPU Workload Guidance for Video Encoding ====\n")
    print("CPU Encoding:")
    print("  - Better for: Quality-focused encoding, complex encoding settings")
    print("  - Advantages: Higher quality at same bitrate, more encoding options")
    print("  - Disadvantages: Much slower than GPU encoding")
    print("  - Use when: Quality is priority over speed, need specific encoding features")
    print("  - Best for: Production-quality renders, archival purposes")
    print("\nGPU Encoding:")
    print("  - Better for: Speed-focused encoding, batch processing, live streaming")
    print("  - Advantages: 3-10x faster than CPU encoding, lower power consumption")
    print("  - Disadvantages: Slightly lower quality at same bitrate")
    print("  - Use when: Speed is priority, encoding many videos, real-time needs")
    print("  - Best for: Content distribution, large batch encodes, time-sensitive work")
    print("\nRecommended Settings:")
    print("  - For CPU: Use slower presets (veryslow, slow) for best quality")
    print("  - For GPU: Use NVENC with moderate bitrates, -cq:v 18-23 for good balance")
    print("\nFor this application:")
    print("  - Large batch encoding jobs: Use GPU (--use_gpu=True)")
    print("  - Individual high-quality encodes: Use CPU (--use_gpu=False)")

# Main function
def main():
    args = parse_args()
    
    # Show CPU vs GPU guidance if requested
    if len(sys.argv) == 1 or '--help' in sys.argv:
        print_encoding_guidance()
    
    # Handle sample video listing
    if args.download_sample == 'list':
        print("Available sample videos:")
        for key, video in SAMPLE_VIDEOS.items():
            print(f"  {key}: {video['description']} ({video['size_mb']} MB)")
        return
        
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Handle sample video download
    if args.download_sample:
        downloaded_path = download_sample_video(args.download_sample, args.input)
        if not downloaded_path:
            logger.error("Failed to download sample video. Exiting.")
            return
        logger.info(f"Successfully downloaded sample video to {downloaded_path}")
        
    # Handle custom URL download
    if args.url:
        filename = args.url.split('/')[-1]
        output_path = os.path.join(args.input, filename)
        if download_file(args.url, output_path):
            logger.info(f"Successfully downloaded video from URL to {output_path}")
        else:
            logger.error("Failed to download video from URL. Continuing with existing files.")
    
    # Parse requested formats
    formats = [f.strip() for f in args.formats.split(',') if f.strip() in RESOLUTION_PRESETS]
    if not formats:
        logger.error(f"No valid formats specified. Available formats: {', '.join(RESOLUTION_PRESETS.keys())}")
        return
    
    logger.info("Starting video encoding batch job")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Target formats: {', '.join(formats)}")
    logger.info(f"Using GPU: {args.use_gpu}")
    logger.info(f"Parallel workers: {args.workers}")
    
    # Find all video files
    video_pattern = os.path.join(args.input, f"**/*.{args.extension}")
    video_files = glob.glob(video_pattern, recursive=True)
    
    if not video_files:
        logger.warning(f"No {args.extension} files found in {args.input}")
        return
        
    logger.info(f"Found {len(video_files)} videos to process")
    
    # Process videos in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for video_path in video_files:
            future = executor.submit(
                process_video, 
                video_path, 
                args.output, 
                formats, 
                args.use_gpu,
                args.crf
            )
            futures[future] = video_path
            
        # Process results as they complete
        successful = 0
        for future in concurrent.futures.as_completed(futures):
            video_path = futures[future]
            try:
                if future.result():
                    successful += 1
            except Exception as e:
                logger.error(f"Error processing {os.path.basename(video_path)}: {str(e)}")
    
    logger.info(f"Encoding complete. Successfully processed {successful}/{len(video_files)} videos.")

if __name__ == '__main__':
    main()

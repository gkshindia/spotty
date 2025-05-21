#!/usr/bin/env python
# Script to download sample video files for encoding tests

import os
import argparse
import urllib.request
import sys

# Define sample videos with name, URL, and approximate size
SAMPLE_VIDEOS = {
    "big_buck_bunny_720p": {
        "url": "https://download.blender.org/peach/bigbuckbunny_movies/big_buck_bunny_720p_surround.avi",
        "size_mb": 184,
        "description": "Big Buck Bunny 720p (Blender Foundation)",
    },
    "tears_of_steel_1080p": {
        "url": "https://download.blender.org/tears/tears_of_steel_1080p.mov",
        "size_mb": 788,
        "description": "Tears of Steel 1080p (Blender Foundation)",
    },
    "sintel_trailer_2k": {
        "url": "https://download.blender.org/durian/trailer/sintel_trailer-2k.mp4",
        "size_mb": 80,
        "description": "Sintel Trailer 2K (Blender Foundation)",
    },
}


# Progress bar for download
class DownloadProgressBar:
    def __init__(self, total_size):
        self.total_size = total_size
        self.downloaded = 0
        self.prev_percent = 0

    def update(self, count):
        self.downloaded += count
        percent = int(self.downloaded * 100 / self.total_size)
        if percent > self.prev_percent:
            self.prev_percent = percent
            chars = int(percent / 2)
            progress_bar = f"[{'#' * chars}{' ' * (50 - chars)}] {percent}%"
            print(f"\r{progress_bar}", end="", flush=True)


# Download a file with progress bar
def download_file(url, output_path):
    try:
        print(f"\nDownloading from {url}")
        print(f"Saving to {output_path}")

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Start the download with a progress bar
        with urllib.request.urlopen(url) as response:
            file_size = int(response.info().get("Content-Length", 0))
            progress_bar = DownloadProgressBar(file_size)

            with open(output_path, "wb") as out_file:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    progress_bar.update(len(chunk))

            print("\nDownload complete!")
            return True
    except Exception as e:
        print(f"\nError downloading file: {str(e)}")
        return False


# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Download sample videos for encoding")
    parser.add_argument(
        "--video",
        type=str,
        choices=list(SAMPLE_VIDEOS.keys()),
        default="big_buck_bunny_720p",
        help="Sample video to download",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./input/sample",
        help="Output directory for downloaded video",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available sample videos and exit"
    )
    return parser.parse_args()


# Main function
def main():
    args = parse_args()

    # List available videos if requested
    if args.list:
        print("Available sample videos:")
        for key, video in SAMPLE_VIDEOS.items():
            print(f"  {key}: {video['description']} ({video['size_mb']} MB)")
        return

    # Download the selected video
    video = SAMPLE_VIDEOS[args.video]
    output_path = os.path.join(
        args.output, f"{args.video}.{video['url'].split('.')[-1]}"
    )

    print(f"Selected video: {video['description']}")
    print(f"File size: ~{video['size_mb']} MB")

    # Confirm download
    if input(f"Download this video? (y/n): ").lower() != "y":
        print("Download canceled.")
        return

    # Perform the download
    download_file(video["url"], output_path)


if __name__ == "__main__":
    main()

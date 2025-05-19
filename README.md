# Spotty Video Encoding Project

This repository is set up for batch video encoding using [Spotty](https://spotty.cloud/), a tool for running compute-intensive workloads in the cloud using AWS Spot Instances. The project is designed to convert high-definition videos to multiple lower-definition formats, optimized to run on either CPU or GPU instances.

## Project Structure

```
.
├── spotty.yaml         # Spotty configuration file
├── encode_videos.py    # Video encoding script
├── requirements.txt   # Python dependencies
├── aws_config.md      # AWS credentials configuration guide
├── input/             # Directory for source videos
│   └── sample/        # Sample videos that will be synced
├── output/            # Directory for encoded videos
```

## Features

- Batch conversion of videos to multiple resolutions (4K, 1080p, 720p, 480p, 360p, 240p)
- Support for both CPU and GPU-accelerated encoding
- Parallel processing for faster encoding
- Auto-skipping of already encoded videos for resumable operations
- Intelligent handling of source resolution (won't upscale)
- AWS Spot Instance support for cost-effective cloud encoding

## Getting Started

### Installation

1. Install Spotty:

```bash
pip install -U spotty
```

2. Dependencies required:
   - FFmpeg: This is included in the Docker container but should be installed locally for testing
   - For AWS: Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/installing.html) and configure it (see aws_config.md)
   - For local: Make sure [Docker](https://docs.docker.com/get-docker/) is installed

3. Place your source videos in the `input/` directory

### AWS Credentials

Refer to the `aws_config.md` file for detailed instructions on setting up AWS credentials. Options include:

- Using AWS CLI configuration (recommended)
- Environment variables
- Using a .env file (included in .gitignore)

The spotty.yaml configuration supports specifying an AWS profile if you have multiple credential sets.

### Running on AWS GPU

```bash
# Start an AWS GPU instance with the specified configuration
spotty start aws-gpu

# Connect to the instance via SSH
spotty sh aws-gpu

# Run the encoding with GPU acceleration
spotty run encode-gpu

# Stop the instance when you're done
spotty stop aws-gpu
```

### Running on AWS CPU

```bash
# Start an AWS CPU instance
spotty start aws-cpu

# Connect to the instance
spotty sh aws-cpu

# Run the encoding using CPU
spotty run encode

# Stop the instance
spotty stop aws-cpu
```

### Running Locally

```bash
# Start Docker container locally
spotty start local

# Connect to the container
spotty sh local

# Run the encoding script
spotty run encode

# Stop the container
spotty stop local
```

## Encoding Options

You can customize the encoding process by modifying the script arguments:

```bash
# Encode to specific formats
python encode_videos.py --formats=1080p,720p,480p

# Use GPU acceleration
python encode_videos.py --use_gpu=True

# Process a specific input directory
python encode_videos.py --input=/data/input/special_videos --output=/data/output/special

# Adjust video quality (lower CRF = higher quality, higher CRF = smaller files)
python encode_videos.py --crf=18  # High quality
python encode_videos.py --crf=28  # Smaller file size
```

## Customization

You can modify the `spotty.yaml` file to:

1. Change the instance types (e.g., more powerful GPU instances)
2. Use different regions or availability zones
3. Configure larger volumes for big encoding jobs
4. Add custom scripts for pre/post-processing

You can also modify the `encode_videos.py` script to change encoding parameters, add additional formats, or integrate with other services like S3 for storage.

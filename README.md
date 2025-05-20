# SpottyCloud - Distributed Computing Platform

SpottyCloud is a lightweight system for managing distributed computing tasks across low-cost cloud servers (AWS Spot Instances). This solution allows teams to run different types of workloads while ensuring resilience to server failures.

## Features

- **Orchestration**: Automated management of AWS Spot Instances
- **Cost Optimization**: Use of cost-effective AWS Spot Instances
- **Resilience**: Automatic recovery from instance terminations
- **Workload Management**: Support for video encoding, machine learning, and other compute-intensive tasks
- **Web Interface**: Modern FastAPI-based dashboard for managing workloads and instances
- **API-Driven**: RESTful API for integrating with other tools and services
- **Resource Monitoring**: Track resource usage and costs

## Project Structure

```
.
├── api/                    # FastAPI Web Application
│   ├── routers/            # API route handlers
│   ├── static/             # Static assets for web UI
│   ├── templates/          # HTML templates
│   └── main.py             # FastAPI entry point
├── docker/                 # Docker configurations
│   ├── Dockerfile.encoding # Container for video encoding
│   ├── Dockerfile.train    # Container for ML training
│   └── Dockerfile.edge     # Container for edge simulations
├── spotty_cloud/           # SpottyCloud core functionality
│   ├── config/             # Configuration management
│   ├── core/               # Core orchestration logic
│   ├── utils/              # Utility modules
│   └── workloads/          # Workload definitions and runners
├── Dockerfile              # Main application Dockerfile
├── spotty.yaml             # Spotty configuration
└── requirements.txt        # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.8 or newer
- Docker
- AWS account (for cloud features)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/spotty-cloud.git
cd spotty-cloud
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up AWS credentials (optional):

- Create a `.env` file with your AWS credentials:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_preferred_region
```

### Running Locally

#### Using Python directly:

```bash
# Start the FastAPI server
uvicorn api.main:app --reload

# Open your browser at http://localhost:8000
```

#### Using Docker:

```bash
# Build the Docker image
docker build -t spotty-cloud .

# Run the container
docker run -p 8000:8000 -v $(pwd)/data:/data spotty-cloud
```

### Accessing the Web Interface

- Main Dashboard: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Using the API

SpottyCloud provides a RESTful API for managing instances, workloads, and scripts:

### Instances

- `GET /api/instances` - List all instances
- `GET /api/instances/{instance_id}` - Get specific instance
- `POST /api/instances` - Request a new instance
- `DELETE /api/instances/{instance_id}` - Terminate an instance

### Workloads

- `GET /api/workloads` - List all workloads
- `GET /api/workloads/{workload_id}` - Get specific workload
- `POST /api/workloads` - Submit a new workload

### Scripts

- `GET /api/scripts` - List available scripts
- `POST /api/scripts/execute` - Execute a script
- `GET /api/scripts/executions/{execution_id}` - Get script execution status

For full API documentation, visit the Swagger UI at http://localhost:8000/docs or ReDoc at http://localhost:8000/redoc.

## Running on AWS

SpottyCloud is designed to work with AWS Spot Instances for cost-effective computing:

```bash
# Start SpottyCloud with AWS orchestrator enabled
uvicorn api.main:app --env-file .env
```

By default, SpottyCloud will manage around 3-4 spot instances, optimizing for both cost and performance.

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

## Configuration

You can configure SpottyCloud through the `spotty_cloud/config/spotty_cloud.yaml` file or via environment variables:

```yaml
system:
  log_level: INFO
  dashboard_port: 8080
  min_instances: 1
  max_instances: 4  # Reduced from 10 for cost optimization

aws:
  instance_types:
    cpu: ["c5.medium", "t3.medium"]  # Smaller instance types
    gpu: ["g4dn.large"]  # Smaller GPU instance
  max_price_multiplier: 1.2
```

## Development

### Directory Structure

- `api/`: FastAPI application for web interface and RESTful API
- `spotty_cloud/core/`: Core orchestration logic
  - `instances/`: Instance management
  - `orchestrator/`: Multi-server orchestration
  - `resilience/`: Failure recovery mechanisms
- `spotty_cloud/workloads/`: Workload definitions and execution

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The [Spotty](https://spotty.cloud/) project for inspiration
- AWS EC2 Spot Instances for enabling cost-effective compute

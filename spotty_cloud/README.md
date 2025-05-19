# SpottyCloud: Distributed Computing on AWS Spot Instances

A lightweight system for managing distributed computing tasks across low-cost cloud servers (AWS Spot Instances). This solution allows teams to experiment with running different types of workloads while learning how to handle sudden server failures gracefully.

## Key Features

### Cost-Efficient Resource Management
- Automatically deploys applications on discounted cloud servers (Spot Instances)
- Balances workloads across servers to minimize costs

### Flexible Workload Support
- Runs regular computing tasks (CPU-based programs)
- Handles graphics-intensive tasks (GPU-required jobs)
- Simulates edge computing scenarios (remote location testing)

### Failure Testing Capabilities
- Allows manual triggering of server shutdowns to test recovery processes
- Provides tools to monitor how systems react to unexpected failures

### User-Friendly Monitoring
- Displays real-time status of all active servers
- Shows cost savings compared to regular cloud pricing
- Tracks success/failure rates of computing tasks

## Project Structure

```
spotty_cloud/
├── core/                     # Core system functionality
│   ├── orchestrator/         # Multi-server orchestration
│   ├── resilience/           # Failure recovery mechanisms
│   └── instances/            # Instance management
├── api/                      # RESTful API interface
├── workloads/                # Workload templates and runners
│   ├── templates/            # Pre-configured workload templates
│   └── runners/              # Execution logic for workloads
├── dashboard/                # Web-based monitoring dashboard
│   ├── frontend/             # UI components
│   └── backend/              # Dashboard API and data processing
├── utils/                    # Utilities and helpers
│   ├── monitoring/           # System monitoring tools
│   ├── cost/                 # Cost tracking and estimation
│   └── backup/               # Data backup mechanisms
├── config/                   # System configuration
│   ├── templates/            # Configuration templates
│   └── profiles/             # Environment profiles
└── tests/                    # Test suites
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

## Installation

```bash
# Clone the repository
git clone <repository-url>

# Install dependencies
pip install -r requirements.txt

# Set up AWS credentials
aws configure
```

## Quick Start

```bash
# Start the orchestrator
python -m spotty_cloud.main --config=config/default.yaml

# Access the dashboard
open http://localhost:8080
```

## Documentation

- [User Guide](docs/user_guide.md)
- [API Reference](docs/api_reference.md)
- [Workload Templates](docs/workload_templates.md)
- [Troubleshooting](docs/troubleshooting.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

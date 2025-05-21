#!/usr/bin/env python
# Edge Computing Simulation Script

import argparse
import time
import os
import json
import logging
import random
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/data/logs/edge_simulation.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("edge_simulation")


class SensorDataGenerator:
    """Generates simulated sensor data for edge computing tests"""

    def __init__(self, sensor_type):
        self.sensor_type = sensor_type

    def generate_data(self):
        """Generate a simulated data point based on sensor type"""
        timestamp = datetime.now().isoformat()

        if self.sensor_type == "camera":
            return {
                "timestamp": timestamp,
                "sensor_type": "camera",
                "resolution": random.choice(["640x480", "1280x720", "1920x1080"]),
                "light_level": random.uniform(0, 100),
                "motion_detected": random.choice([True, False]),
                "objects_detected": random.randint(0, 10),
            }

        elif self.sensor_type == "temperature":
            return {
                "timestamp": timestamp,
                "sensor_type": "temperature",
                "temperature_c": random.uniform(15, 35),
                "humidity": random.uniform(30, 90),
                "pressure": random.uniform(980, 1030),
            }

        elif self.sensor_type == "motion":
            return {
                "timestamp": timestamp,
                "sensor_type": "motion",
                "movement_detected": random.choice([True, False]),
                "intensity": random.uniform(0, 10),
                "direction": random.uniform(0, 359),
            }

        elif self.sensor_type == "audio":
            return {
                "timestamp": timestamp,
                "sensor_type": "audio",
                "decibel_level": random.uniform(20, 100),
                "speech_detected": random.choice([True, False]),
                "frequencies": [random.uniform(20, 20000) for _ in range(5)],
            }

        else:
            return {
                "timestamp": timestamp,
                "sensor_type": "generic",
                "value": random.random(),
            }


class EdgeProcessor:
    """Processes sensor data in an edge computing environment"""

    def __init__(self, sensor_type, processing_mode, output_dir):
        self.sensor_type = sensor_type
        self.processing_mode = processing_mode
        self.output_dir = output_dir
        self.data_generator = SensorDataGenerator(sensor_type)
        self.data_points = 0
        self.checkpoint_counter = 0

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("/data/logs", exist_ok=True)
        os.makedirs("/data/checkpoints", exist_ok=True)

    def process_data(self):
        """Process a single data point"""
        data = self.data_generator.generate_data()

        # Simulate processing time
        if self.processing_mode == "realtime":
            # Faster processing for real-time mode
            time.sleep(random.uniform(0.05, 0.2))
        else:
            # More intensive processing for batch mode
            time.sleep(random.uniform(0.2, 0.5))

        # Add processed fields
        data["processed"] = True
        data["processing_time"] = time.time()

        # Add simulated processed results based on sensor type
        if self.sensor_type == "camera":
            data["analysis_result"] = {
                "image_processed": True,
                "classifications": ["person", "car", "tree"]
                if data.get("objects_detected", 0) > 0
                else [],
            }
        elif self.sensor_type in ["temperature", "motion", "audio"]:
            data["analysis_result"] = {
                "anomaly_detected": random.random() > 0.8,
                "confidence": random.uniform(0.5, 1.0),
            }

        # Save the processed data
        self.data_points += 1
        self.checkpoint_counter += 1

        # Save to output file
        output_file = os.path.join(
            self.output_dir, f"{self.sensor_type}_{int(time.time())}.json"
        )
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(
            f"Processed data point {self.data_points} from {self.sensor_type} sensor"
        )

        # Create checkpoint periodically
        if self.checkpoint_counter >= 30:
            self.save_checkpoint()
            self.checkpoint_counter = 0

        return data

    def save_checkpoint(self):
        """Save processing checkpoint"""
        checkpoint = {
            "sensor_type": self.sensor_type,
            "processing_mode": self.processing_mode,
            "data_points_processed": self.data_points,
            "last_timestamp": datetime.now().isoformat(),
        }

        checkpoint_file = os.path.join(
            "/data/checkpoints", f"{self.sensor_type}_checkpoint.json"
        )
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)

        logger.info(f"Saved checkpoint after {self.data_points} data points")


def main():
    """Main entry point for the edge computing simulation"""
    parser = argparse.ArgumentParser(description="Edge Computing Simulation")
    parser.add_argument(
        "--sensor",
        type=str,
        default="camera",
        choices=["camera", "temperature", "motion", "audio"],
        help="Type of sensor data to simulate",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="realtime",
        choices=["realtime", "batch"],
        help="Processing mode",
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Data collection interval in seconds"
    )
    parser.add_argument(
        "--duration", type=int, default=60, help="Total simulation duration in minutes"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/data/processed",
        help="Output directory for processed data",
    )

    args = parser.parse_args()

    total_iterations = (args.duration * 60) // args.interval

    logger.info(f"Starting edge computing simulation with {args.sensor} sensor")
    logger.info(
        f"Mode: {args.mode}, Interval: {args.interval}s, Duration: {args.duration} minutes"
    )

    processor = EdgeProcessor(args.sensor, args.mode, args.output)

    try:
        for i in range(total_iterations):
            # Process data
            processor.process_data()

            # Sleep until next interval
            time.sleep(args.interval)

        logger.info(
            f"Simulation complete. Processed {processor.data_points} data points."
        )

    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        processor.save_checkpoint()

    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}", exc_info=True)
        processor.save_checkpoint()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

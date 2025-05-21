#!/usr/bin/env python

import logging
import time
import uuid
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError
from spotty_cloud.utils.aws.credentials import AWSCredentialManager

logger = logging.getLogger(__name__)


class SpotInstanceManager:
    """
    Manages AWS Spot Instances lifecycle including requests, monitoring, and termination.
    Integrates with Spotty for actual instance provisioning.
    """

    def __init__(
        self, config: Dict[str, Any], aws_credentials: AWSCredentialManager = None
    ):
        """
        Initialize the Spot Instance Manager

        Args:
            config: Configuration dictionary
            aws_credentials: AWS credential manager instance (optional)
        """
        self.config = config

        aws_config = config.get("aws", {})
        self.vpc_id = aws_config.get("vpc_id", None)
        self.subnet_ids = aws_config.get("subnet_ids", [])
        self.security_group_id = aws_config.get("security_group_id", None)
        self.key_name = aws_config.get("key_name", None)

        self.max_price_multiplier = aws_config.get("spot", {}).get(
            "max_price_multiplier", 1.1
        )
        self.instance_types = aws_config.get("spot", {}).get(
            "instance_types",
            {
                "cpu": ["c5.large", "c5.xlarge"],
                "gpu": ["g4dn.xlarge", "p3.2xlarge"],
                "edge": ["t3.medium", "t3.large"],
            },
        )

        if aws_credentials:
            self.aws_credentials = aws_credentials
        else:
            self.aws_credentials = AWSCredentialManager(aws_config)

        self.session = self.aws_credentials.get_session()
        if not self.session:
            logger.error("Failed to initialize AWS session. Spot operations will fail.")
            self.session = boto3.Session()

        self.region = self.aws_credentials.region
        self.ec2_client = self.session.client("ec2")
        self.ec2_resource = self.session.resource("ec2")

        self.spot_requests = {}
        self.instances = {}

        self._init_spotty_config()

    def _init_spotty_config(self):
        """
        Initialize Spotty configuration templates for different workload types
        """
        self.spotty_base_config = {
            "project": {
                "name": "spotty-cloud-{project_name}",
                "syncFilters": [
                    {"exclude": [".git/*", ".idea/*", "__pycache__/*", ".DS_Store"]}
                ],
            },
            "containers": [
                {
                    "name": "{container_name}",
                    "projectDir": "/workspace/project",
                    "file": "docker/{dockerfile}",
                    "volumeMounts": [
                        {"name": "workspace", "mountPath": "/workspace"},
                        {"name": "data", "mountPath": "/data"},
                    ],
                }
            ],
            "instances": [
                {
                    "name": "{instance_name}",
                    "provider": "aws",
                    "parameters": {
                        "region": self.region,
                        "instanceType": "{instance_type}",
                        "spotInstance": True,
                        "maxPrice": "{max_price}",
                        "volumes": [
                            {"name": "workspace", "size": 10, "mountDir": "/workspace"},
                            {"name": "data", "size": 20, "mountDir": "/data"},
                        ],
                    },
                }
            ],
        }

    def request_instance(
        self, instance_type: str = None, workload_type: str = None
    ) -> Optional[str]:
        """
        Request a new Spot Instance

        Args:
            instance_type: Specific EC2 instance type to request
            workload_type: Type of workload (cpu, gpu, edge) to determine instance type

        Returns:
            request_id: ID of the spot request, or None if request failed
        """
        if not instance_type and workload_type:
            instance_types = self.instance_types.get(
                workload_type, self.instance_types["cpu"]
            )
            instance_type = instance_types[0]
        elif not instance_type:
            instance_type = self.instance_types["cpu"][0]

        request_id = f"sr-{uuid.uuid4().hex[:8]}"
        instance_name = f"spotty-{workload_type or 'default'}-{uuid.uuid4().hex[:6]}"

        # Validate workload type requirements
        is_gpu_instance = "g4dn" in instance_type or "p3" in instance_type
        is_edge_instance = "t3" in instance_type

        if workload_type == "gpu" and not is_gpu_instance:
            logger.warning(
                f"Requested GPU workload but instance type {instance_type} may not have GPU. Switching to g4dn.xlarge"
            )
            instance_type = "g4dn.xlarge"
        elif workload_type == "edge" and not is_edge_instance:
            logger.warning(
                f"Requested edge workload but {instance_type} is not optimized for edge. Switching to t3.medium"
            )
            instance_type = "t3.medium"

        try:
            spot_price = self._get_current_spot_price(instance_type)
            max_price = spot_price * self.max_price_multiplier

            logger.info(
                f"Requesting {instance_type} instance with max price ${max_price:.4f}/hour"
            )

            spotty_config = self._create_spotty_config(
                project_name=instance_name,
                instance_name=instance_name,
                instance_type=instance_type,
                max_price=f"{max_price:.4f}",
                container_name=f"workload-{workload_type or 'default'}",
                dockerfile=f"Dockerfile.{workload_type or 'default'}",
            )

            logger.info(
                f"Simulating Spotty API call to launch {instance_type} instance"
            )

            self.spot_requests[request_id] = {
                "request_id": request_id,
                "instance_name": instance_name,
                "instance_type": instance_type,
                "status": "pending",
                "max_price": max_price,
                "request_time": time.time(),
                "spotty_config": spotty_config,
            }

            return request_id

        except Exception as e:
            logger.error(f"Error requesting spot instance: {str(e)}", exc_info=True)
            return None

    def check_instance_request(self, request_id: str) -> Dict[str, Any]:
        """
        Check the status of a spot instance request

        Args:
            request_id: ID of the spot request to check

        Returns:
            status: Dictionary with request status information
        """
        if request_id not in self.spot_requests:
            return {
                "status": "not_found",
                "reason": f"Request ID {request_id} not found",
            }

        request_details = self.spot_requests[request_id]

        try:
            request_age = time.time() - request_details.get("request_time", 0)

            if request_age > 60 and request_details.get("status") == "pending":
                instance_id = f"i-{uuid.uuid4().hex[:8]}"

                self.spot_requests[request_id]["status"] = "fulfilled"
                self.spot_requests[request_id]["instance_id"] = instance_id
                self.spot_requests[request_id]["fulfillment_time"] = time.time()

                self.instances[instance_id] = {
                    "instance_id": instance_id,
                    "instance_type": request_details.get("instance_type"),
                    "request_id": request_id,
                    "status": "pending",
                    "start_time": time.time(),
                    "spotty_name": request_details.get("instance_name"),
                }

                logger.info(
                    f"Request {request_id} fulfilled with instance {instance_id}"
                )

                return {
                    "status": "fulfilled",
                    "instance_id": instance_id,
                    "instance_type": request_details.get("instance_type"),
                }

            return {
                "status": request_details.get("status", "unknown"),
                "age_seconds": request_age,
                "instance_id": request_details.get("instance_id", None),
            }

        except Exception as e:
            logger.error(
                f"Error checking spot request {request_id}: {str(e)}", exc_info=True
            )
            return {"status": "error", "reason": str(e)}

    def get_instance_details(self, instance_id: str) -> Dict[str, Any]:
        """
        Get details about a specific instance

        Args:
            instance_id: ID of the instance to check

        Returns:
            details: Dictionary with instance details
        """
        if instance_id not in self.instances:
            return {
                "status": "not_found",
                "reason": f"Instance {instance_id} not found",
            }

        return self.instances[instance_id]

    def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate a spot instance

        Args:
            instance_id: ID of the instance to terminate

        Returns:
            success: Boolean indicating success
        """
        if instance_id not in self.instances:
            logger.warning(f"Cannot terminate: Instance {instance_id} not found")
            return False

        try:
            instance_details = self.instances[instance_id]
            spotty_name = instance_details.get("spotty_name")

            logger.info(
                f"Simulating Spotty API call to terminate instance {spotty_name} ({instance_id})"
            )

            self.instances[instance_id]["status"] = "terminated"
            self.instances[instance_id]["end_time"] = time.time()

            return True

        except Exception as e:
            logger.error(
                f"Error terminating instance {instance_id}: {str(e)}", exc_info=True
            )
            return False

    def list_active_instances(self) -> List[Dict[str, Any]]:
        """
        List all active instances managed by this SpotInstanceManager

        Returns:
            instances: List of active instance details
        """
        return [
            details
            for instance_id, details in self.instances.items()
            if details.get("status") not in ["terminated", "shutting-down"]
        ]

    def _get_current_spot_price(self, instance_type: str) -> float:
        """
        Get the current spot price for a specific instance type

        Args:
            instance_type: EC2 instance type

        Returns:
            price: Current spot price per hour
        """
        try:
            response = self.ec2_client.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescriptions=["Linux/UNIX"],
                MaxResults=1,
            )

            if response["SpotPriceHistory"]:
                return float(response["SpotPriceHistory"][0]["SpotPrice"])

            return self._get_default_spot_price(instance_type)

        except ClientError as e:
            logger.warning(
                f"AWS API error getting spot price for {instance_type}: {e.response['Error']['Message']}"
            )
            return self._get_default_spot_price(instance_type)
        except Exception as e:
            logger.warning(f"Error getting spot price for {instance_type}: {str(e)}")
            return self._get_default_spot_price(instance_type)

    def _get_default_spot_price(self, instance_type: str) -> float:
        """
        Get a default estimated spot price when API call fails

        Args:
            instance_type: EC2 instance type

        Returns:
            price: Estimated spot price per hour
        """
        price_map = {
            "t3.medium": 0.0125,
            "t3.large": 0.0250,
            "c5.large": 0.0320,
            "c5.xlarge": 0.0640,
            "g4dn.xlarge": 0.2900,
            "p3.2xlarge": 1.2000,
        }

        return price_map.get(instance_type, 0.05)

    def _create_spotty_config(self, **kwargs) -> Dict[str, Any]:
        """
        Create a Spotty configuration from the template

        Args:
            **kwargs: Values to substitute in the template

        Returns:
            config: Dictionary with the Spotty configuration
        """
        import json
        import copy

        config = copy.deepcopy(self.spotty_base_config)

        config_str = json.dumps(config)
        for key, value in kwargs.items():
            config_str = config_str.replace(f"{{{key}}}", str(value))

        return json.loads(config_str)

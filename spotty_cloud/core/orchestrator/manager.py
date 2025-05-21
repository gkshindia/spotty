#!/usr/bin/env python

import logging
import threading
import time
import queue
from typing import Dict, Any

from spotty_cloud.core.instances.spot_manager import SpotInstanceManager
from spotty_cloud.core.resilience.recovery import RecoveryManager
from spotty_cloud.utils.monitoring.instance_monitor import InstanceMonitor
from spotty_cloud.utils.cost.tracker import CostTracker
from spotty_cloud.utils.aws.credentials import AWSCredentialManager
from spotty_cloud.workloads.runners.dispatcher import WorkloadDispatcher

logger = logging.getLogger(__name__)


class OrchestratorManager:
    """
    Manages multiple Spot instances and orchestrates workloads across them.
    Handles scaling, distribution, and failure recovery.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator with configuration

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.instance_pool_size = config.get("orchestrator", {}).get(
            "instance_pool_size", 5
        )
        self.min_instances = config.get("orchestrator", {}).get("min_instances", 3)
        self.max_instances = config.get("orchestrator", {}).get("max_instances", 3)
        self.polling_interval = config.get("orchestrator", {}).get(
            "polling_interval", 30
        )

        self.aws_credentials = AWSCredentialManager(config.get("aws", {}))

        self.instance_manager = SpotInstanceManager(
            config, aws_credentials=self.aws_credentials
        )
        self.recovery_manager = RecoveryManager(config)
        self.instance_monitor = InstanceMonitor(
            config, aws_credentials=self.aws_credentials
        )
        self.cost_tracker = CostTracker(config, aws_credentials=self.aws_credentials)
        self.workload_dispatcher = WorkloadDispatcher(config)

        self.active_instances = {}
        self.pending_instances = {}
        self.instance_workloads = {}
        self.workload_queue = queue.Queue()

        self.running = False
        self.main_thread = None

        self._validate_aws_credentials()

    def _validate_aws_credentials(self):
        """
        Validate that AWS credentials are properly configured
        """
        is_valid, message = self.aws_credentials.get_credentials_status()
        if not is_valid:
            logger.warning(f"AWS credentials issue: {message}")
            logger.warning(
                "Some features may not work correctly without valid AWS credentials"
            )
        else:
            logger.info(f"AWS credentials: {message}")

    def start(self):
        """
        Start the orchestrator and all its components
        """
        if self.running:
            logger.warning("Orchestrator is already running")
            return

        logger.info("Starting orchestrator components...")

        self.cost_tracker.start()

        self.instance_monitor.start()

        self.recovery_manager.start()

        self.workload_dispatcher.start()

        self.running = True
        self.main_thread = threading.Thread(target=self._orchestration_loop)
        self.main_thread.daemon = True
        self.main_thread.start()

        logger.info(
            f"Orchestrator started, targeting {self.instance_pool_size} instances"
        )

        self._ensure_minimum_instances()

    def stop(self):
        """
        Stop the orchestrator and all its components
        """
        if not self.running:
            logger.warning("Orchestrator is not running")
            return

        logger.info("Stopping orchestrator...")
        self.running = False

        if self.main_thread:
            self.main_thread.join(timeout=30)

        self.workload_dispatcher.stop()
        self.recovery_manager.stop()
        self.instance_monitor.stop()
        self.cost_tracker.stop()

        logger.info("Orchestrator stopped")

    def wait(self):
        """
        Wait for the orchestrator to complete
        """
        if self.main_thread:
            self.main_thread.join()

    def submit_workload(self, workload_config: Dict[str, Any]):
        """
        Submit a new workload to be executed

        Args:
            workload_config: Configuration for the workload

        Returns:
            workload_id: Unique identifier for the submitted workload
        """
        workload_id = self.workload_dispatcher.create_workload(workload_config)
        self.workload_queue.put(workload_id)
        logger.info(f"Workload {workload_id} submitted to queue")
        return workload_id

    def get_workload_status(self, workload_id: str):
        """
        Get the status of a workload

        Args:
            workload_id: ID of the workload to check

        Returns:
            status: Status information for the workload
        """
        return self.workload_dispatcher.get_workload_status(workload_id)

    def get_instance_status(self, instance_id=None):
        """
        Get status of all instances or a specific instance

        Args:
            instance_id: (Optional) Specific instance ID to check

        Returns:
            status: Instance status information
        """
        if instance_id and instance_id in self.active_instances:
            return self.active_instances[instance_id]
        return self.active_instances

    def get_system_status(self):
        """
        Get overall system status

        Returns:
            status: Dictionary with system status information
        """
        aws_valid, _ = self.aws_credentials.get_credentials_status()

        health_status = "healthy"
        if not self.running:
            health_status = "stopped"
        elif not aws_valid:
            health_status = "degraded"

        return {
            "active_instances": len(self.active_instances),
            "pending_instances": len(self.pending_instances),
            "running_workloads": self.workload_dispatcher.get_count_by_status(
                "running"
            ),
            "queued_workloads": self.workload_queue.qsize(),
            "health": health_status,
            "aws_credentials": aws_valid,
            "aws_region": self.aws_credentials.region,
            "cost_data": self.cost_tracker.get_summary()
            if hasattr(self, "cost_tracker")
            else None,
        }

    def trigger_instance_failure(self, instance_id: str):
        """
        Manually trigger a failure for testing resilience

        Args:
            instance_id: ID of the instance to terminate

        Returns:
            success: Boolean indicating success
        """
        if instance_id not in self.active_instances:
            logger.warning(f"Cannot trigger failure: Instance {instance_id} not found")
            return False

        logger.info(f"Manually triggering failure for instance {instance_id}")
        return self.instance_manager.terminate_instance(instance_id)

    def _orchestration_loop(self):
        """
        Main orchestration loop that manages instances and workloads
        """
        while self.running:
            try:
                self._check_instance_health()

                self._update_instance_status()

                self._scale_instances()

                self._distribute_workloads()

                time.sleep(self.polling_interval)

            except Exception as e:
                logger.error(f"Error in orchestration loop: {str(e)}", exc_info=True)
                time.sleep(10)

    def _check_instance_health(self):
        """
        Check health of all active instances and handle any failures
        """
        for instance_id, instance_details in list(self.active_instances.items()):
            health_status = self.instance_monitor.check_instance(instance_id)

            if health_status.get("status") != "healthy":
                logger.warning(
                    f"Instance {instance_id} is unhealthy: {health_status.get('reason', 'unknown')}"
                )

                self._handle_instance_failure(
                    instance_id, health_status.get("reason", "unknown")
                )

    def _handle_instance_failure(self, instance_id: str, reason: str):
        """
        Handle a failed instance by initiating recovery process

        Args:
            instance_id: ID of the failed instance
            reason: Reason for failure
        """
        logger.info(f"Handling failure of instance {instance_id}: {reason}")

        affected_workloads = self.instance_workloads.get(instance_id, [])

        self.recovery_manager.handle_instance_failure(
            instance_id, affected_workloads, reason
        )

        for workload_id in affected_workloads:
            logger.info(f"Requeuing workload {workload_id} after instance failure")
            self.workload_queue.put(workload_id)

        if instance_id in self.active_instances:
            del self.active_instances[instance_id]
        if instance_id in self.instance_workloads:
            del self.instance_workloads[instance_id]

        self._request_replacement_instance()

    def _request_replacement_instance(self):
        """
        Request a replacement instance after a failure
        """
        logger.info("Requesting replacement instance")
        instance_type = self.config.get("instances", {}).get("default_type", "c5.large")

        request_id = self.instance_manager.request_instance(instance_type)
        if request_id:
            self.pending_instances[request_id] = {
                "request_time": time.time(),
                "instance_type": instance_type,
                "status": "pending",
            }
            logger.info(f"Replacement instance requested with ID {request_id}")
        else:
            logger.error("Failed to request replacement instance")

    def _update_instance_status(self):
        """
        Update status of pending instances and add newly available ones to the pool
        """
        for request_id, request_details in list(self.pending_instances.items()):
            status = self.instance_manager.check_instance_request(request_id)

            if status.get("status") == "fulfilled":
                instance_id = status.get("instance_id")
                logger.info(
                    f"Instance request {request_id} fulfilled with instance ID {instance_id}"
                )

                self.active_instances[instance_id] = {
                    "id": instance_id,
                    "type": request_details.get("instance_type"),
                    "start_time": time.time(),
                    "status": "initializing",
                    "workloads": [],
                }

                self.instance_workloads[instance_id] = []

                del self.pending_instances[request_id]

            elif status.get("status") == "failed":
                logger.warning(
                    f"Instance request {request_id} failed: {status.get('reason', 'unknown')}"
                )
                del self.pending_instances[request_id]

                self._request_replacement_instance()

    def _ensure_minimum_instances(self):
        """
        Ensure we have at least the minimum number of instances
        """
        current_count = len(self.active_instances) + len(self.pending_instances)
        needed = max(0, self.min_instances - current_count)

        if needed > 0:
            logger.info(f"Requesting {needed} instances to meet minimum requirement")

            for _ in range(needed):
                self._request_replacement_instance()

    def _scale_instances(self):
        """
        Scale the number of instances based on workload queue and current instances
        """
        current_count = len(self.active_instances) + len(self.pending_instances)
        queue_size = self.workload_queue.qsize()

        target_instances = min(
            self.max_instances,
            max(self.min_instances, self.instance_pool_size, queue_size // 2),
        )

        if current_count < target_instances:
            instances_to_add = target_instances - current_count
            logger.info(f"Scaling up: Adding {instances_to_add} instances")

            for _ in range(instances_to_add):
                self._request_replacement_instance()

        elif current_count > target_instances + 2:
            instances_to_remove = current_count - target_instances
            logger.info(
                f"Scaling down: Target is {target_instances}, current is {current_count}"
            )
            self._terminate_excess_instances(instances_to_remove)

    def _distribute_workloads(self):
        """
        Distribute pending workloads to available instances
        """
        available_instances = [
            instance_id
            for instance_id, details in self.active_instances.items()
            if details.get("status") == "ready"
            and len(self.instance_workloads.get(instance_id, [])) < 3
        ]

        if not available_instances and not self.workload_queue.empty():
            logger.info("No available instances for workload distribution")
            return

        while available_instances and not self.workload_queue.empty():
            try:
                workload_id = self.workload_queue.get_nowait()

                instance_id = available_instances.pop(0)

                logger.info(
                    f"Assigning workload {workload_id} to instance {instance_id}"
                )
                success = self.workload_dispatcher.dispatch_workload(
                    workload_id, instance_id
                )

                if success:
                    self.instance_workloads[instance_id].append(workload_id)
                    self.active_instances[instance_id]["workloads"].append(workload_id)
                else:
                    logger.warning(
                        f"Failed to dispatch workload {workload_id}, requeuing"
                    )
                    self.workload_queue.put(workload_id)

                if len(self.instance_workloads.get(instance_id, [])) >= 3:
                    continue

                available_instances.append(instance_id)

            except queue.Empty:
                break

    def _terminate_excess_instances(self, count: int):
        """
        Terminate excess instances for scaling down

        Args:
            count: Number of instances to terminate
        """
        if count <= 0:
            return

        # Prioritize instances with no workloads
        idle_instances = []
        busy_instances = []

        for instance_id, instance_details in self.active_instances.items():
            if (
                instance_id in self.instance_workloads
                and len(self.instance_workloads[instance_id]) > 0
            ):
                # Instance has assigned workloads
                busy_instances.append((instance_id, instance_details))
            else:
                # Idle instance
                idle_instances.append((instance_id, instance_details))

        # Sort idle instances by start time (oldest first)
        idle_instances.sort(key=lambda x: x[1].get("start_time", 0))

        # Terminate instances up to count
        instances_terminated = 0

        # First terminate idle instances
        for instance_id, _ in idle_instances:
            if instances_terminated >= count:
                break

            logger.info(f"Terminating idle instance {instance_id} for scaling down")
            if self._terminate_instance(instance_id):
                instances_terminated += 1

        # If needed, terminate busy instances too (starting with instances with fewest workloads)
        if instances_terminated < count:
            # Sort busy instances by number of workloads (ascending)
            busy_instances.sort(
                key=lambda x: len(self.instance_workloads.get(x[0], []))
            )

            remaining = count - instances_terminated
            for instance_id, _ in busy_instances[:remaining]:
                logger.info(
                    f"Terminating instance {instance_id} with workloads for scaling down"
                )
                if self._terminate_instance(instance_id):
                    instances_terminated += 1

        logger.info(f"Terminated {instances_terminated} instances for scaling down")

    def _terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate an instance and clean up related resources

        Args:
            instance_id: ID of the instance to terminate

        Returns:
            success: Boolean indicating success
        """
        if instance_id not in self.active_instances:
            logger.warning(f"Cannot terminate: Instance {instance_id} not found")
            return False

        # Terminate instance through instance manager
        success = self.instance_manager.terminate_instance(instance_id)
        if not success:
            logger.error(f"Failed to terminate instance {instance_id}")
            return False

        # Handle affected workloads
        affected_workloads = []
        if instance_id in self.instance_workloads:
            affected_workloads = self.workload_dispatcher.handle_instance_failure(
                instance_id
            )

        # Deregister from monitoring
        self.instance_monitor.deregister_instance(instance_id)

        # Deregister from cost tracking
        self.cost_tracker.deregister_instance(instance_id)

        # Remove from active instances
        instance_details = self.active_instances.pop(instance_id, {})

        # Log termination
        logger.info(
            f"Instance {instance_id} terminated ({len(affected_workloads)} affected workloads)"
        )

        return True

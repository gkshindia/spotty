#!/usr/bin/env python
# Instance Monitor - Tracks health and performance of instances

import logging
import time
import threading
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError
from utils.aws.credentials import AWSCredentialManager

logger = logging.getLogger(__name__)

class InstanceMonitor:
    """
    Monitors the health and performance of Spot Instances.
    Detects potential failures and termination notices.
    """
    
    def __init__(self, config: Dict[str, Any], aws_credentials: AWSCredentialManager = None):
        """
        Initialize the Instance Monitor
        
        Args:
            config: Configuration dictionary
            aws_credentials: AWS credential manager instance (optional)
        """
        self.config = config
        
        # Monitoring configuration
        monitoring_config = config.get('monitoring', {})
        self.monitoring_interval = monitoring_config.get('interval', 30)  # seconds
        self.metrics_enabled = monitoring_config.get('metrics_enabled', True)
        self.alert_thresholds = monitoring_config.get('thresholds', {
            'cpu_high': 90,
            'memory_high': 85,
            'disk_high': 90
        })
        
        # Set up AWS credentials
        if aws_credentials:
            self.aws_credentials = aws_credentials
        else:
            self.aws_credentials = AWSCredentialManager(config.get('aws', {}))
            
        # Get boto3 session from credential manager
        self.session = self.aws_credentials.get_session()
        if not self.session:
            logger.error("Failed to initialize AWS session. Instance monitoring will be limited.")
            self.session = boto3.Session()  # Empty session as fallback
        
        self.region = self.aws_credentials.region
        self.ec2_client = self.session.client('ec2')
        self.cloudwatch_client = self.session.client('cloudwatch')
        
        # Internal state
        self.instances = {}  # instance_id -> health_details
        self.spot_termination_notices = {}  # instance_id -> termination_time
        
        # Control flags
        self.running = False
        self.monitoring_thread = None
        
    def start(self):
        """
        Start the instance monitoring thread
        """
        if self.running:
            logger.warning("Instance Monitor is already running")
            return
            
        logger.info("Starting Instance Monitor...")
        self.running = True
        
        # Start the monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info(f"Instance monitoring thread started with interval {self.monitoring_interval} seconds")
        
    def stop(self):
        """
        Stop the instance monitoring thread
        """
        if not self.running:
            logger.warning("Instance Monitor is not running")
            return
            
        logger.info("Stopping Instance Monitor...")
        self.running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=30)
            
        logger.info("Instance Monitor stopped")
        
    def register_instance(self, instance_id: str, instance_type: str) -> bool:
        """
        Register a new instance for monitoring
        
        Args:
            instance_id: ID of the instance
            instance_type: EC2 instance type
            
        Returns:
            success: Boolean indicating success
        """
        if instance_id in self.instances:
            logger.warning(f"Instance {instance_id} is already registered for monitoring")
            return False
            
        # Register the instance
        self.instances[instance_id] = {
            'instance_id': instance_id,
            'instance_type': instance_type,
            'status': 'initializing',
            'health': 'unknown',
            'metrics': {},
            'last_check': time.time(),
            'checks_passed': 0,
            'checks_failed': 0
        }
        
        logger.info(f"Registered instance {instance_id} for monitoring")
        return True
        
    def deregister_instance(self, instance_id: str) -> bool:
        """
        Deregister an instance from monitoring
        
        Args:
            instance_id: ID of the instance
            
        Returns:
            success: Boolean indicating success
        """
        if instance_id not in self.instances:
            logger.warning(f"Instance {instance_id} is not registered for monitoring")
            return False
            
        # Deregister the instance
        del self.instances[instance_id]
        
        # Also remove from termination notices if present
        if instance_id in self.spot_termination_notices:
            del self.spot_termination_notices[instance_id]
            
        logger.info(f"Deregistered instance {instance_id} from monitoring")
        return True
        
    def check_instance(self, instance_id: str) -> Dict[str, Any]:
        """
        Check the health of a specific instance
        
        Args:
            instance_id: ID of the instance to check
            
        Returns:
            health: Dictionary with health information
        """
        if instance_id not in self.instances:
            return {
                'status': 'not_found',
                'health': 'unknown',
                'message': f"Instance {instance_id} is not registered for monitoring"
            }
            
        # Return cached health check results
        instance_details = self.instances[instance_id]
        
        # Check if instance has a termination notice
        if instance_id in self.spot_termination_notices:
            termination_time = self.spot_termination_notices[instance_id]
            time_remaining = termination_time - time.time()
            
            return {
                'status': 'terminating',
                'health': 'terminating',
                'termination_time': termination_time,
                'time_remaining_seconds': max(0, int(time_remaining)),
                'message': f"Instance scheduled for termination in {max(0, int(time_remaining))} seconds"
            }
            
        return {
            'status': instance_details.get('status', 'unknown'),
            'health': instance_details.get('health', 'unknown'),
            'metrics': instance_details.get('metrics', {}),
            'last_check': instance_details.get('last_check', 0),
            'checks_passed': instance_details.get('checks_passed', 0),
            'checks_failed': instance_details.get('checks_failed', 0),
            'message': instance_details.get('message', '')
        }
        
    def get_all_instances_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health information for all monitored instances
        
        Returns:
            instances_health: Dictionary mapping instance IDs to health information
        """
        result = {}
        
        for instance_id in self.instances:
            result[instance_id] = self.check_instance(instance_id)
            
        return result
        
    def get_instances_with_termination_notice(self) -> Dict[str, float]:
        """
        Get instances that have received a termination notice
        
        Returns:
            termination_notices: Dictionary mapping instance IDs to termination times
        """
        return self.spot_termination_notices.copy()
        
    def _monitoring_loop(self):
        """
        Background thread that periodically checks instance health
        """
        logger.info("Starting instance monitoring loop")
        
        while self.running:
            try:
                # Check for spot termination notices
                self._check_spot_termination_notices()
                
                # Check instance health
                self._check_instance_health()
                
                # Update instance metrics if enabled
                if self.metrics_enabled:
                    self._update_instance_metrics()
                    
                # Sleep until next check
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}", exc_info=True)
                time.sleep(30)  # Sleep longer if there was an error
                
    def _check_spot_termination_notices(self):
        """
        Check for spot instance termination notices
        """
        for instance_id in list(self.instances.keys()):
            try:
                # In a real implementation, we would check the EC2 metadata endpoint
                # for the instance. Since we can't actually do that in this simulation,
                # we'll randomly simulate spot termination notices for testing purposes.
                
                # TODO: Implement actual termination notice detection in production code
                # For now, use a simulated approach for testing resilience
                if self.config.get('simulation', {}).get('simulate_terminations', False):
                    import random
                    if instance_id not in self.spot_termination_notices and random.random() < 0.01:  # 1% chance per check
                        # Simulate a termination notice with 2 minutes warning
                        termination_time = time.time() + 120  # 2 minutes from now
                        self.spot_termination_notices[instance_id] = termination_time
                        
                        logger.warning(f"Simulated termination notice for instance {instance_id} at {time.ctime(termination_time)}")
                
            except Exception as e:
                logger.error(f"Error checking termination notice for instance {instance_id}: {str(e)}")
                
    def _check_instance_health(self):
        """
        Check the health of all instances
        """
        for instance_id in list(self.instances.keys()):
            try:
                # Get current details
                instance_details = self.instances[instance_id]
                
                # In a real implementation, we would check the instance status via AWS API
                # and potentially also application-level health checks
                
                try:
                    # Check EC2 instance status
                    response = self.ec2_client.describe_instance_status(
                        InstanceIds=[instance_id],
                        IncludeAllInstances=True
                    )
                    
                    if response['InstanceStatuses']:
                        status = response['InstanceStatuses'][0]
                        instance_state = status['InstanceState']['Name']
                        instance_status = status['InstanceStatus']['Status']
                        system_status = status['SystemStatus']['Status']
                        
                        # Determine overall health
                        if instance_state == 'running' and instance_status == 'ok' and system_status == 'ok':
                            health = 'healthy'
                            instance_details['checks_passed'] += 1
                        else:
                            health = 'unhealthy'
                            instance_details['checks_failed'] += 1
                            instance_details['message'] = f"Instance state: {instance_state}, status: {instance_status}, system: {system_status}"
                            
                        # Update instance details
                        instance_details['status'] = instance_state
                        instance_details['health'] = health
                        instance_details['last_check'] = time.time()
                        
                    else:
                        # Instance not found or no status available
                        instance_details['status'] = 'unknown'
                        instance_details['health'] = 'unknown'
                        instance_details['message'] = "No status information available"
                        instance_details['last_check'] = time.time()
                        instance_details['checks_failed'] += 1
                        
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'InvalidInstanceID.NotFound':
                        # Instance no longer exists
                        instance_details['status'] = 'terminated'
                        instance_details['health'] = 'terminated'
                        instance_details['message'] = "Instance no longer exists"
                        instance_details['last_check'] = time.time()
                        instance_details['checks_failed'] += 1
                    else:
                        raise
                        
            except Exception as e:
                logger.error(f"Error checking health for instance {instance_id}: {str(e)}")
                
                # Update with error status
                if instance_id in self.instances:
                    self.instances[instance_id]['health'] = 'error'
                    self.instances[instance_id]['message'] = f"Health check error: {str(e)}"
                    self.instances[instance_id]['last_check'] = time.time()
                    self.instances[instance_id]['checks_failed'] += 1
                    
    def _update_instance_metrics(self):
        """
        Update performance metrics for all instances
        """
        for instance_id in list(self.instances.keys()):
            try:
                # In a real implementation, we would fetch CloudWatch metrics for the instance
                # such as CPU utilization, memory usage, disk I/O, network traffic, etc.
                
                # TODO: Implement actual metrics collection in production code
                # For now, use simulated metrics for testing
                
                # Skip metrics collection for non-running instances
                if self.instances[instance_id].get('status') != 'running':
                    continue
                    
                # Generate simulated metrics
                import random
                metrics = {
                    'cpu_utilization': random.uniform(5, 95),
                    'memory_utilization': random.uniform(20, 80),
                    'disk_utilization': random.uniform(10, 70),
                    'network_in': random.uniform(0.1, 10),  # MB/s
                    'network_out': random.uniform(0.1, 5)   # MB/s
                }
                
                # Check for threshold violations
                alerts = []
                if metrics['cpu_utilization'] > self.alert_thresholds.get('cpu_high', 90):
                    alerts.append(f"High CPU utilization: {metrics['cpu_utilization']:.1f}%")
                    
                if metrics['memory_utilization'] > self.alert_thresholds.get('memory_high', 85):
                    alerts.append(f"High memory utilization: {metrics['memory_utilization']:.1f}%")
                    
                if metrics['disk_utilization'] > self.alert_thresholds.get('disk_high', 90):
                    alerts.append(f"High disk utilization: {metrics['disk_utilization']:.1f}%")
                    
                # Update instance metrics
                self.instances[instance_id]['metrics'] = metrics
                self.instances[instance_id]['alerts'] = alerts
                
                # Log any alerts
                if alerts:
                    logger.warning(f"Instance {instance_id} has {len(alerts)} alerts: {', '.join(alerts)}")
                    
            except Exception as e:
                logger.error(f"Error updating metrics for instance {instance_id}: {str(e)}")

#!/usr/bin/env python
# Workload Dispatcher - Handles distributing workloads to instances

import logging
import time
import uuid
import threading
import queue
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class WorkloadDispatcher:
    """
    Manages workload distribution across instances, tracks execution status,
    and handles completion or failure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Workload Dispatcher
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Dispatcher configuration
        self.max_retries = config.get('workloads', {}).get('max_retries', 3)
        self.check_interval = config.get('workloads', {}).get('check_interval', 30)  # seconds
        
        # Internal state
        self.workloads = {}  # workload_id -> workload_details
        self.instance_workloads = {}  # instance_id -> [workload_ids]
        self.completion_callbacks = {}  # workload_id -> callback
        
        # Control flags
        self.running = False
        self.dispatch_thread = None
        self.status_queue = queue.Queue()  # Queue for status updates
        
    def start(self):
        """
        Start the workload dispatcher
        """
        if self.running:
            logger.warning("Workload Dispatcher is already running")
            return
            
        logger.info("Starting Workload Dispatcher...")
        self.running = True
        
        # Start the dispatch thread
        self.dispatch_thread = threading.Thread(target=self._dispatch_loop)
        self.dispatch_thread.daemon = True
        self.dispatch_thread.start()
        
        logger.info("Workload Dispatcher started")
        
    def stop(self):
        """
        Stop the workload dispatcher
        """
        if not self.running:
            logger.warning("Workload Dispatcher is not running")
            return
            
        logger.info("Stopping Workload Dispatcher...")
        self.running = False
        
        if self.dispatch_thread:
            self.dispatch_thread.join(timeout=30)
            
        logger.info("Workload Dispatcher stopped")
        
    def create_workload(self, workload_config: Dict[str, Any]) -> str:
        """
        Create a new workload for execution
        
        Args:
            workload_config: Configuration for the workload
            
        Returns:
            workload_id: Unique identifier for the workload
        """
        # Generate unique workload ID
        workload_id = f"wl-{uuid.uuid4().hex[:12]}"
        
        # Extract workload type and parameters
        workload_type = workload_config.get('type', 'generic')
        cpu_allocation = workload_config.get('resources', {}).get('cpu', 1)
        memory_allocation = workload_config.get('resources', {}).get('memory', 1)
        gpu_allocation = workload_config.get('resources', {}).get('gpu', 0)
        timeout = workload_config.get('timeout', 3600)  # Default 1 hour timeout
        
        # Create workload record
        self.workloads[workload_id] = {
            'id': workload_id,
            'type': workload_type,
            'config': workload_config,
            'resources': {
                'cpu': cpu_allocation,
                'memory': memory_allocation,
                'gpu': gpu_allocation
            },
            'status': 'pending',
            'create_time': time.time(),
            'start_time': None,
            'end_time': None,
            'timeout': timeout,
            'instance_id': None,
            'retries': 0,
            'logs': [],
            'result': None
        }
        
        logger.info(f"Created workload {workload_id} of type {workload_type}")
        return workload_id
        
    def dispatch_workload(self, workload_id: str, instance_id: str) -> bool:
        """
        Dispatch a workload to a specific instance
        
        Args:
            workload_id: ID of the workload to dispatch
            instance_id: ID of the instance to dispatch to
            
        Returns:
            success: Boolean indicating success
        """
        if workload_id not in self.workloads:
            logger.warning(f"Workload {workload_id} not found")
            return False
            
        workload = self.workloads[workload_id]
        
        # Check if workload is in a dispatchable state
        if workload['status'] not in ['pending', 'failed']:
            logger.warning(f"Workload {workload_id} is in status {workload['status']}, not dispatchable")
            return False
            
        logger.info(f"Dispatching workload {workload_id} to instance {instance_id}")
        
        try:
            # Update workload status
            workload['status'] = 'dispatching'
            workload['instance_id'] = instance_id
            
            # Add to instance workloads
            if instance_id not in self.instance_workloads:
                self.instance_workloads[instance_id] = []
            self.instance_workloads[instance_id].append(workload_id)
            
            # TODO: Actually dispatch the workload to the instance
            # For now, simulate the dispatch process
            
            # Update status to running
            workload['status'] = 'running'
            workload['start_time'] = time.time()
            
            # Start a monitoring thread to simulate execution
            threading.Thread(
                target=self._simulate_workload_execution,
                args=(workload_id, instance_id)
            ).start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error dispatching workload {workload_id}: {str(e)}", exc_info=True)
            
            # Update status to failed
            workload['status'] = 'failed'
            workload['logs'].append(f"Dispatch error: {str(e)}")
            
            return False
            
    def get_workload_status(self, workload_id: str) -> Dict[str, Any]:
        """
        Get the status of a workload
        
        Args:
            workload_id: ID of the workload to check
            
        Returns:
            status: Dictionary with workload status information
        """
        if workload_id not in self.workloads:
            return {
                'status': 'not_found',
                'message': f"Workload {workload_id} not found"
            }
            
        workload = self.workloads[workload_id]
        return {
            'id': workload_id,
            'type': workload.get('type'),
            'status': workload.get('status'),
            'instance_id': workload.get('instance_id'),
            'create_time': workload.get('create_time'),
            'start_time': workload.get('start_time'),
            'end_time': workload.get('end_time'),
            'duration': self._calculate_duration(workload),
            'retries': workload.get('retries', 0),
            'result': workload.get('result')
        }
        
    def get_instance_workloads(self, instance_id: str) -> List[str]:
        """
        Get the workloads assigned to a specific instance
        
        Args:
            instance_id: ID of the instance
            
        Returns:
            workload_ids: List of workload IDs assigned to the instance
        """
        return self.instance_workloads.get(instance_id, [])
        
    def get_running_count(self) -> int:
        """
        Get the count of currently running workloads
        
        Returns:
            count: Number of running workloads
        """
        return sum(1 for wl in self.workloads.values() if wl.get('status') == 'running')
        
    def register_completion_callback(self, workload_id: str, callback) -> bool:
        """
        Register a callback function to be called when a workload completes
        
        Args:
            workload_id: ID of the workload
            callback: Function to call on completion (takes workload_id and status as arguments)
            
        Returns:
            success: Boolean indicating success
        """
        if workload_id not in self.workloads:
            logger.warning(f"Cannot register callback: Workload {workload_id} not found")
            return False
            
        self.completion_callbacks[workload_id] = callback
        return True
        
    def handle_instance_failure(self, instance_id: str) -> List[str]:
        """
        Handle the failure of an instance by marking its workloads as failed
        
        Args:
            instance_id: ID of the failed instance
            
        Returns:
            affected_workloads: List of affected workload IDs
        """
        affected_workloads = self.instance_workloads.get(instance_id, [])
        
        if not affected_workloads:
            logger.info(f"No workloads affected by failure of instance {instance_id}")
            return []
            
        logger.info(f"Handling failure of instance {instance_id} with {len(affected_workloads)} affected workloads")
        
        for workload_id in affected_workloads:
            if workload_id in self.workloads:
                workload = self.workloads[workload_id]
                
                if workload.get('status') == 'running':
                    # Mark as failed
                    workload['status'] = 'failed'
                    workload['logs'].append(f"Failed due to instance {instance_id} failure")
                    workload['end_time'] = time.time()
                    
                    # Increment retry count
                    workload['retries'] += 1
                    
                    # Check if we should retry
                    if workload['retries'] < self.max_retries:
                        logger.info(f"Workload {workload_id} will be retried (attempt {workload['retries'] + 1}/{self.max_retries})")
                        workload['status'] = 'pending'  # Mark for retry
                    else:
                        logger.warning(f"Workload {workload_id} has failed permanently after {workload['retries']} retries")
                        workload['status'] = 'failed'
                        
                        # Call completion callback if registered
                        if workload_id in self.completion_callbacks:
                            try:
                                self.completion_callbacks[workload_id](workload_id, 'failed')
                                del self.completion_callbacks[workload_id]
                            except Exception as e:
                                logger.error(f"Error in completion callback for workload {workload_id}: {str(e)}")
        
        # Clear instance workloads
        self.instance_workloads[instance_id] = []
        
        return affected_workloads
        
    def _dispatch_loop(self):
        """
        Background thread that processes status updates and handles workload completion
        """
        logger.info("Starting workload dispatch loop")
        
        while self.running:
            try:
                # Process status updates from the queue
                self._process_status_updates()
                
                # Check for timed-out workloads
                self._check_workload_timeouts()
                
                # Sleep briefly before next iteration
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in dispatch loop: {str(e)}", exc_info=True)
                time.sleep(10)  # Sleep longer if there was an error
                
    def _process_status_updates(self):
        """
        Process workload status updates from the queue
        """
        while not self.status_queue.empty():
            try:
                # Get the next status update
                update = self.status_queue.get_nowait()
                
                # Process the update
                workload_id = update.get('workload_id')
                status = update.get('status')
                result = update.get('result')
                message = update.get('message', '')
                
                if workload_id in self.workloads:
                    workload = self.workloads[workload_id]
                    
                    # Update workload status
                    workload['status'] = status
                    workload['logs'].append(message)
                    
                    if status in ['completed', 'failed']:
                        workload['end_time'] = time.time()
                        workload['result'] = result
                        
                        logger.info(f"Workload {workload_id} {status}: {message}")
                        
                        # Remove from instance workloads
                        instance_id = workload.get('instance_id')
                        if instance_id and instance_id in self.instance_workloads:
                            if workload_id in self.instance_workloads[instance_id]:
                                self.instance_workloads[instance_id].remove(workload_id)
                                
                        # Call completion callback if registered
                        if workload_id in self.completion_callbacks:
                            try:
                                self.completion_callbacks[workload_id](workload_id, status)
                                del self.completion_callbacks[workload_id]
                            except Exception as e:
                                logger.error(f"Error in completion callback for workload {workload_id}: {str(e)}")
                                
            except queue.Empty:
                break
                
    def _check_workload_timeouts(self):
        """
        Check for workloads that have exceeded their timeout
        """
        current_time = time.time()
        
        for workload_id, workload in list(self.workloads.items()):
            # Only check running workloads
            if workload.get('status') != 'running':
                continue
                
            # Check if timeout has elapsed
            start_time = workload.get('start_time', 0)
            timeout = workload.get('timeout', 3600)  # Default 1 hour timeout
            
            if start_time and (current_time - start_time) > timeout:
                logger.warning(f"Workload {workload_id} has timed out after {timeout} seconds")
                
                # Update workload status
                workload['status'] = 'failed'
                workload['logs'].append(f"Timed out after {timeout} seconds")
                workload['end_time'] = current_time
                
                # Add to status queue for processing
                self.status_queue.put({
                    'workload_id': workload_id,
                    'status': 'failed',
                    'result': None,
                    'message': f"Timed out after {timeout} seconds"
                })
                
    def _simulate_workload_execution(self, workload_id: str, instance_id: str):
        """
        Simulate the execution of a workload for testing purposes
        
        Args:
            workload_id: ID of the workload
            instance_id: ID of the instance
        """
        if workload_id not in self.workloads:
            return
            
        workload = self.workloads[workload_id]
        workload_type = workload.get('type', 'generic')
        
        # Simulate different execution times based on workload type
        if workload_type == 'quick':
            execution_time = 10  # 10 seconds
        elif workload_type == 'medium':
            execution_time = 30  # 30 seconds
        elif workload_type == 'long':
            execution_time = 60  # 60 seconds
        elif workload_type == 'gpu':
            execution_time = 45  # 45 seconds
        else:
            execution_time = 20  # Default 20 seconds
            
        logger.info(f"Simulating execution of {workload_type} workload {workload_id} for {execution_time} seconds")
        
        # Add progress updates to the logs
        for progress in [25, 50, 75]:
            # Skip if workload was already completed or failed
            if workload_id not in self.workloads or self.workloads[workload_id].get('status') != 'running':
                return
                
            # Sleep for part of the execution time
            time.sleep(execution_time / 4)
            
            # Add progress log
            if workload_id in self.workloads:
                self.workloads[workload_id]['logs'].append(f"Progress: {progress}%")
                logger.debug(f"Workload {workload_id} progress: {progress}%")
                
        # Final sleep
        time.sleep(execution_time / 4)
        
        # Skip if workload was already completed or failed
        if workload_id not in self.workloads or self.workloads[workload_id].get('status') != 'running':
            return
            
        # Generate simulated result based on workload type
        if workload_type == 'quick':
            result = {'output': 'Quick task completed', 'data': [1, 2, 3]}
        elif workload_type == 'medium':
            result = {'output': 'Medium task completed', 'data': {'key': 'value'}}
        elif workload_type == 'long':
            result = {'output': 'Long task completed', 'processed_items': 1000}
        elif workload_type == 'gpu':
            result = {'output': 'GPU task completed', 'accuracy': 0.95, 'iterations': 100}
        else:
            result = {'output': 'Task completed'}
            
        # Add to status queue
        self.status_queue.put({
            'workload_id': workload_id,
            'status': 'completed',
            'result': result,
            'message': f"Workload {workload_type} completed successfully"
        })
        
    def _calculate_duration(self, workload: Dict[str, Any]) -> Optional[float]:
        """
        Calculate the duration of a workload in seconds
        
        Args:
            workload: Workload details dictionary
            
        Returns:
            duration: Duration in seconds, or None if still running
        """
        start_time = workload.get('start_time')
        end_time = workload.get('end_time')
        
        if start_time is None:
            return None
            
        if end_time is None:
            # If still running, calculate current duration
            return time.time() - start_time
            
        return end_time - start_time

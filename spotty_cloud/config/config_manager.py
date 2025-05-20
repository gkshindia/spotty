#!/usr/bin/env python
# Configuration Manager for SpottyCloud

import os
import yaml
import logging
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration and templates for SpottyCloud"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize the configuration manager
        
        Args:
            config_path: Path to the main configuration file
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'spotty_cloud.yaml'
        )
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'templates'
        )
        self.config = self._load_main_config()
        self.templates = self._load_templates()
    
    def _load_main_config(self) -> dict[str, Any]:
        """
        Load the main configuration file
        
        Returns:
            dict: Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load configuration from {self.config_path}: {str(e)}")
            logger.warning("Using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration
        
        Returns:
            dict: Default configuration dictionary
        """
        return {
            'system': {
                'log_level': 'INFO',
                'dashboard_port': 8080,
                'min_instances': 1,
                'max_instances': 10,
                'scaling_cooldown': 300  # 5 minutes
            },
            'aws': {
                'region': 'ap-south-1',
                'default_image_id': 'ami-0c55b159cbfafe1f0',  # Amazon Linux 2
                'instance_types': {
                    'cpu': ['c5.large', 't3.medium'],
                    'gpu': ['g4dn.xlarge']
                },
                'availability_zones': ['ap-south-1a', 'ap-south-1b', 'ap-south-1c'],
                'max_price_multiplier': 1.2  # Max price as multiplier of on-demand
            },
            'workloads': {
                'queue_polling_interval': 10,  # seconds
                'max_queue_size': 100,
                'default_timeout': 3600,  # 1 hour
                'default_retries': 3
            },
            'resilience': {
                'termination_check_interval': 5,  # seconds
                'backup_frequency': 60,  # seconds
                'max_recovery_time': 300  # 5 minutes
            },
            'monitoring': {
                'instance_check_interval': 30,  # seconds
                'workload_check_interval': 15,  # seconds
                'cost_update_interval': 300  # 5 minutes
            }
        }
    
    def _load_templates(self) -> dict[str, Any]:
        """
        Load all workload templates from the templates directory
        
        Returns:
            dict: Dictionary of template name -> template config
        """
        templates = {}
        template_dir = Path(self.templates_dir)
        
        if not template_dir.exists():
            logger.warning(f"Templates directory does not exist: {self.templates_dir}")
            return templates
        
        for template_file in template_dir.glob('*.yaml'):
            try:
                with open(template_file, 'r') as f:
                    template = yaml.safe_load(f)
                    template_name = template.get('name')
                    if template_name:
                        templates[template_name] = template
                        logger.info(f"Loaded template '{template_name}' from {template_file}")
                    else:
                        logger.warning(f"Template file {template_file} has no name field, skipping")
            except Exception as e:
                logger.error(f"Error loading template {template_file}: {str(e)}")
        
        logger.info(f"Loaded {len(templates)} templates")
        return templates
    
    def get_template(self, template_name: str) -> Optional[dict[str, Any]]:
        """
        Get a specific template by name
        
        Args:
            template_name: Name of the template
            
        Returns:
            dict: Template configuration or None if not found
        """
        return self.templates.get(template_name)
    
    def get_all_templates(self) -> dict[str, Any]:
        """
        Get all available templates
        
        Returns:
            dict: Dictionary of all templates
        """
        return self.templates
    
    def get_system_config(self) -> dict[str, Any]:
        """
        Get system configuration
        
        Returns:
            dict: System configuration
        """
        return self.config.get('system', {})
    
    def get_aws_config(self) -> dict[str, Any]:
        """
        Get AWS configuration
        
        Returns:
            dict: AWS configuration
        """
        return self.config.get('aws', {})
    
    def get_workload_config(self) -> dict[str, Any]:
        """
        Get workload configuration
        
        Returns:
            dict: Workload configuration
        """
        return self.config.get('workloads', {})
    
    def get_resilience_config(self) -> dict[str, Any]:
        """
        Get resilience configuration
        
        Returns:
            dict: Resilience configuration
        """
        return self.config.get('resilience', {})
    
    def get_monitoring_config(self) -> dict[str, Any]:
        """
        Get monitoring configuration
        
        Returns:
            dict: Monitoring configuration
        """
        return self.config.get('monitoring', {})
    
    def get_appropriate_instance_type(self, workload_template: str) -> str:
        """
        Get the appropriate instance type for a workload template
        
        Args:
            workload_template: Name of the workload template
            
        Returns:
            str: Instance type best suited for the workload
        """
        template = self.get_template(workload_template)
        if not template:
            logger.warning(f"Unknown template: {workload_template}, using default CPU instance")
            return self.config.get('aws', {}).get('instance_types', {}).get('cpu', ['t3.medium'])[0]
        
        # Check if GPU is required
        requires_gpu = template.get('resources', {}).get('gpu', 0) > 0
        if requires_gpu:
            gpu_instances = self.config.get('aws', {}).get('instance_types', {}).get('gpu', [])
            if gpu_instances:
                return gpu_instances[0]
            # Fallback if GPU is requested but none are configured
            logger.warning("GPU requested but no GPU instances configured, using CPU instance")
        
        # Use CPU instance
        cpu_instances = self.config.get('aws', {}).get('instance_types', {}).get('cpu', [])
        if cpu_instances:
            return cpu_instances[0]
        
        # Fallback
        return 't3.medium'
    
    def update_config(self, config_updates: dict[str, Any]) -> None:
        """
        Update specific configuration settings
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        # Deep merge the updates into the current config
        self._deep_update(self.config, config_updates)
        
        # Save the updated config
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                logger.info(f"Saved updated configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {str(e)}")
    
    def _deep_update(self, d: dict[str, Any], u: dict[str, Any]) -> None:
        """
        Deep update dictionary d with values from dictionary u
        
        Args:
            d: Dictionary to update
            u: Dictionary with updates
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v

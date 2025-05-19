#!/usr/bin/env python

import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class AWSCredentialManager:
    """Manages AWS credentials for SpottyCloud services"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the AWS credential manager
        
        Args:
            config: Configuration dictionary with AWS settings
        """
        self.config = config or {}
        self.credentials_valid = False
        self.session = None
        self.region = self._get_region()
        self.initialized = self._initialize_credentials()
    
    def _get_region(self) -> str:
        """
        Get AWS region from config, environment variable, or default
        
        Returns:
            str: AWS region
        """
        region = self.config.get('region')
        if not region:
            region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
        
        return region or 'us-west-2'
    
    def _initialize_credentials(self) -> bool:
        """
        Initialize AWS credentials from various sources
        
        Returns:
            bool: True if credentials were initialized successfully
        """
        # Try to initialize session
        try:
            # Check if credentials are provided in config
            if 'aws_access_key_id' in self.config and 'aws_secret_access_key' in self.config:
                self.session = boto3.Session(
                    aws_access_key_id=self.config['aws_access_key_id'],
                    aws_secret_access_key=self.config['aws_secret_access_key'],
                    region_name=self.region
                )
                logger.info("Initialized AWS session from config credentials")
                return self._validate_credentials()
            
            # Try to get credentials from environment variables
            elif (os.environ.get('AWS_ACCESS_KEY_ID') and 
                  os.environ.get('AWS_SECRET_ACCESS_KEY')):
                # boto3 will automatically use these environment variables
                self.session = boto3.Session(region_name=self.region)
                logger.info("Initialized AWS session from environment variables")
                return self._validate_credentials()
            
            # Try to get credentials from AWS CLI config or EC2 instance role
            else:
                self.session = boto3.Session(region_name=self.region)
                logger.info("Initialized AWS session from AWS CLI config or instance role")
                return self._validate_credentials()
                
        except Exception as e:
            logger.error(f"Failed to initialize AWS credentials: {str(e)}")
            return False
    
    def _validate_credentials(self) -> bool:
        """
        Validate AWS credentials by making a simple API call
        
        Returns:
            bool: True if credentials are valid
        """
        try:
            # Try a simple API call
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            
            account_id = identity.get('Account')
            self.credentials_valid = True
            logger.info(f"AWS credentials validated for account {account_id}")
            return True
        except ClientError as e:
            logger.error(f"AWS credentials validation failed: {str(e)}")
            self.credentials_valid = False
            return False
    
    def get_session(self) -> Optional[boto3.Session]:
        """
        Get the initialized boto3 session
        
        Returns:
            boto3.Session: Initialized session or None if initialization failed
        """
        if not self.initialized:
            logger.warning("AWS credentials were not properly initialized")
        return self.session
    
    def get_client(self, service_name: str) -> Any:
        """
        Get a boto3 client for the specified service
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 's3')
            
        Returns:
            boto3 client for the specified service
        """
        if not self.session:
            raise ValueError("AWS session not initialized")
        return self.session.client(service_name)
    
    def get_resource(self, service_name: str) -> Any:
        """
        Get a boto3 resource for the specified service
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 's3')
            
        Returns:
            boto3 resource for the specified service
        """
        if not self.session:
            raise ValueError("AWS session not initialized")
        return self.session.resource(service_name)
    
    def get_account_id(self) -> Optional[str]:
        """
        Get AWS account ID
        
        Returns:
            str: AWS account ID or None if unavailable
        """
        try:
            if not self.session:
                return None
            sts = self.session.client('sts')
            return sts.get_caller_identity().get('Account')
        except Exception as e:
            logger.error(f"Error getting account ID: {str(e)}")
            return None
    
    def get_credentials_status(self) -> Tuple[bool, str]:
        """
        Get current credentials status
        
        Returns:
            Tuple[bool, str]: Status (valid/invalid) and message
        """
        if not self.initialized:
            return False, "AWS credentials not initialized"
        elif not self.credentials_valid:
            return False, "AWS credentials invalid or insufficient permissions"
        else:
            return True, "AWS credentials valid and ready"
    
    @staticmethod
    def get_instance_identity() -> Dict[str, Any]:
        """
        Get instance identity information (useful for Spot Instances)
        
        Returns:
            Dict: Instance identity document or empty dict if not running on EC2
        """
        try:
            # This URL is only accessible from within an EC2 instance
            import requests
            response = requests.get(
                'http://169.254.169.254/latest/dynamic/instance-identity/document',
                timeout=2  # Short timeout to avoid hanging
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}

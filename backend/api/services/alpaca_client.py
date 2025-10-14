#!/usr/bin/env python3
"""
Alpaca Client
Wrapper for Alpaca API with enhanced functionality
"""

import logging
from typing import Dict, Optional, Union

import alpaca_trade_api as tradeapi

from utils.alpaca import AlpacaCredentials

logger = logging.getLogger(__name__)

class AlpacaClient:
    """
    Unified Alpaca API client
    Provides a consistent interface to Alpaca API
    """

    def __init__(self, config: Union[AlpacaCredentials, Dict]):
        """
        Initialize Alpaca client

        Args:
            config: AlpacaCredentials dataclass or dictionary with api_key, secret_key, base_url
        """
        if isinstance(config, AlpacaCredentials):
            self.credentials = config
        else:
            self.credentials = AlpacaCredentials(
                key_id=config['api_key'],
                secret_key=config['secret_key'],
                base_url=config.get('base_url', 'https://paper-api.alpaca.markets')
            )
        self.api = None
        self._connect()

    def _connect(self):
        """Establish connection to Alpaca API"""
        try:
            self.api = tradeapi.REST(
                self.credentials.key_id,
                self.credentials.secret_key,
                self.credentials.base_url,
                api_version='v2'
            )

            # Test connection
            account = self.api.get_account()
            logger.info(f"Connected to Alpaca API. Account status: {account.status}")

        except Exception as e:
            logger.error(f"Failed to connect to Alpaca API: {e}")
            self.api = None
            raise

    def is_connected(self) -> bool:
        """Check if connected to Alpaca API"""
        try:
            if not self.api:
                return False
            self.api.get_account()
            return True
        except:
            return False

    def reconnect(self):
        """Reconnect to Alpaca API"""
        logger.info("Attempting to reconnect to Alpaca API")
        self._connect()

    def get_api(self):
        """Get the raw Alpaca API object"""
        if not self.api:
            self._connect()
        return self.api

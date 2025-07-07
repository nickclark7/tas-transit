"""Exceptions for Tasmanian Transport integration."""
from __future__ import annotations


class TasTransitException(Exception):
    """Base exception for Tasmanian Transport integration."""


class TasTransitApiException(TasTransitException):
    """Exception for API-related errors."""


class TasTransitConfigurationException(TasTransitException):
    """Exception for configuration-related errors."""


class TasTransitDataException(TasTransitException):
    """Exception for data parsing errors."""
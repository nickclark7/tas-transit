#!/usr/bin/env python3
"""Simple test script to verify the TAS Transit integration is working."""

import asyncio
import logging
import sys
sys.path.append("custom_components")

from tas_transit.api import TasTransitApi

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_api():
    """Test the API client directly."""
    api = TasTransitApi()
    
    try:
        # Test with a real stop ID (Hobart Interchange)
        test_stop_id = "7109023"
        logger.info(f"Testing API with stop ID: {test_stop_id}")
        
        # Test stop info
        stop_info = await api.get_stop_info(test_stop_id)
        if stop_info:
            logger.info(f"Stop info retrieved successfully")
            logger.debug(f"Stop info keys: {list(stop_info.keys()) if isinstance(stop_info, dict) else 'Not a dict'}")
        else:
            logger.error("No stop info retrieved")
            return False
        
        # Test departures
        departures = await api.get_stop_departures(test_stop_id)
        logger.info(f"Retrieved {len(departures)} departures")
        
        if departures:
            first_departure = departures[0]
            logger.info(f"First departure: {first_departure}")
            
            # Test keys we expect
            expected_keys = ["lineNumber", "destinationName", "scheduledMinutesUntilDeparture"]
            missing_keys = [key for key in expected_keys if key not in first_departure]
            if missing_keys:
                logger.warning(f"Missing expected keys in departure data: {missing_keys}")
            else:
                logger.info("All expected keys found in departure data")
        else:
            logger.warning("No departures found - this might be normal if no buses are scheduled")
            
        return True
        
    except Exception as e:
        logger.error(f"API test failed: {e}")
        return False
    finally:
        await api.close()

async def main():
    """Run the test."""
    logger.info("Starting TAS Transit API test...")
    success = await test_api()
    
    if success:
        logger.info("✅ API test completed successfully!")
        return 0
    else:
        logger.error("❌ API test failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
"""Pytest configuration and shared fixtures for HCDP MCP Server tests."""

import pytest
import os
from unittest.mock import patch


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "HCDP_API_TOKEN": "test_api_token",
        "HCDP_BASE_URL": "https://test.api.hcdp.com"
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def sample_raster_response():
    """Sample response for raster data endpoint."""
    return {
        "status": "success",
        "data": {
            "url": "https://example.com/raster.tiff",
            "download_id": "dl_123"
        },
        "metadata": {
            "variable": "rainfall",
            "aggregation": "month",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "location": "hawaii",
            "units": "mm",
            "grid_resolution": "250m",
            "projection": "EPSG:4326"
        }
    }


@pytest.fixture
def sample_timeseries_response():
    """Sample response for timeseries data endpoint."""
    return {
        "data": [
            {"date": "2023-01-01", "value": 125.5, "unit": "mm"},
            {"date": "2023-02-01", "value": 98.2, "unit": "mm"},
            {"date": "2023-03-01", "value": 156.8, "unit": "mm"},
            {"date": "2023-04-01", "value": 203.4, "unit": "mm"},
            {"date": "2023-05-01", "value": 89.7, "unit": "mm"},
            {"date": "2023-06-01", "value": 45.3, "unit": "mm"}
        ],
        "metadata": {
            "latitude": 21.3099,
            "longitude": -157.8581,
            "variable": "rainfall",
            "aggregation": "month",
            "location": "hawaii"
        }
    }


@pytest.fixture
def sample_station_response():
    """Sample response for station data endpoint."""
    return {
        "stations": [
            {
                "id": "STAT001",
                "name": "Honolulu International Airport",
                "latitude": 21.3187,
                "longitude": -157.9224,
                "elevation": 5.0,
                "measurements": [
                    {"date": "2023-01-01", "value": 125.5, "quality": "good"},
                    {"date": "2023-02-01", "value": 98.2, "quality": "good"},
                    {"date": "2023-03-01", "value": 156.8, "quality": "fair"}
                ]
            },
            {
                "id": "STAT002", 
                "name": "Haleakala Summit",
                "latitude": 20.7097,
                "longitude": -156.2533,
                "elevation": 3055.0,
                "measurements": [
                    {"date": "2023-01-01", "value": 45.2, "quality": "good"},
                    {"date": "2023-02-01", "value": 32.1, "quality": "good"},
                    {"date": "2023-03-01", "value": 67.4, "quality": "poor"}
                ]
            }
        ],
        "metadata": {
            "variable": "rainfall",
            "aggregation": "month",
            "location": "hawaii",
            "total_stations": 2
        }
    }


@pytest.fixture
def sample_mesonet_response():
    """Sample response for mesonet data endpoint."""
    return {
        "measurements": [
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "station": "MESA001",
                "station_name": "Kona Airport Mesonet",
                "value": 15.2,
                "unit": "m/s",
                "quality": "good"
            },
            {
                "timestamp": "2023-01-01T01:00:00Z",
                "station": "MESA001", 
                "station_name": "Kona Airport Mesonet",
                "value": 12.8,
                "unit": "m/s",
                "quality": "good"
            },
            {
                "timestamp": "2023-01-01T02:00:00Z",
                "station": "MESA001",
                "station_name": "Kona Airport Mesonet", 
                "value": 18.5,
                "unit": "m/s",
                "quality": "fair"
            }
        ],
        "metadata": {
            "variable": "wind_speed",
            "station": "MESA001",
            "aggregation": "day",
            "location": "hawaii",
            "total_measurements": 24
        }
    }


@pytest.fixture
def sample_data_package_response():
    """Sample response for data package generation endpoint."""
    return {
        "package_id": "pkg_abc123",
        "status": "processing",
        "estimated_completion": "2023-01-01T12:00:00Z",
        "download_url": None,
        "email_delivery": True,
        "package_size_mb": 125.6,
        "included_files": [
            "rainfall_2023_01_hawaii_month.tiff",
            "rainfall_2023_02_hawaii_month.tiff", 
            "rainfall_2023_03_hawaii_month.tiff",
            "metadata.json"
        ]
    }


@pytest.fixture
def valid_variables():
    """List of valid climate variables supported by HCDP API."""
    return [
        "rainfall",
        "temp_mean", 
        "temp_min",
        "temp_max",
        "relative_humidity",
        "spi",
        "ndvi_modis",
        "ignition_probability"
    ]


@pytest.fixture
def valid_locations():
    """List of valid locations supported by HCDP API."""
    return ["hawaii", "american_samoa"]


@pytest.fixture
def valid_aggregations():
    """List of valid temporal aggregations supported by HCDP API."""
    return ["day", "month", "year"]


@pytest.fixture
def valid_formats():
    """List of valid output formats supported by HCDP API."""
    return ["tiff", "json", "csv"]


@pytest.fixture
def hawaii_coordinates():
    """Sample coordinates within Hawaii bounds."""
    return [
        (21.3099, -157.8581),  # Honolulu
        (20.7097, -156.2533),  # Haleakala
        (19.7297, -155.0900),  # Hilo
        (21.9743, -159.3650),  # Lihue, Kauai
        (20.8893, -156.6906),  # Kahului, Maui
    ]


@pytest.fixture
def american_samoa_coordinates():
    """Sample coordinates within American Samoa bounds."""
    return [
        (-14.3064, -170.6944),  # Pago Pago
        (-14.2846, -170.7365),  # Leone
        (-14.2393, -170.6348),  # Fagatogo
    ]


@pytest.fixture
def sample_date_ranges():
    """Sample date ranges for testing."""
    return [
        ("2023-01-01", "2023-01-31"),  # Single month
        ("2023-01-01", "2023-12-31"),  # Full year
        ("2022-06-01", "2023-05-31"),  # Multi-year span
        ("2023-07-15", "2023-07-15"),  # Single day
    ]
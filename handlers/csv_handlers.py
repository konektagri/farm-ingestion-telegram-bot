"""CSV operations for survey data persistence."""
import csv
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from services.drive_service import get_drive_service

logger = logging.getLogger(__name__)

# Module-level callable for CSV upload (for backward compatibility)
_upload_csv_to_drive_fn: Optional[Callable] = None


def set_upload_csv_fn(fn: Callable) -> None:
    """Set the CSV upload function (backward compatibility)."""
    global _upload_csv_to_drive_fn
    _upload_csv_to_drive_fn = fn


def save_survey_to_csv(
    user_id: int, 
    username: str, 
    survey_data: dict, 
    location_data: dict, 
    date_str: str
) -> None:
    """
    Save survey data to CSV file.
    
    Args:
        user_id: Telegram user ID
        username: Username or display name
        survey_data: Survey responses dictionary
        location_data: Location data with lat/lon/province
        date_str: Date string for the survey
    """
    csv_file = Path('farm_surveys.csv')
    file_exists = csv_file.exists()
    
    # Prepare data row
    row = {
        'timestamp': datetime.now().isoformat(),
        'date': date_str,
        'user_id': user_id,
        'username': username,
        'farm_number': survey_data.get('farm_number', ''),
        'latitude': location_data.get('latitude', ''),
        'longitude': location_data.get('longitude', ''),
        'province': location_data.get('province', ''),
        'rainfall': survey_data.get('rainfall', ''),
        'rainfall_intensity': survey_data.get('rainfall_intensity', ''),
        'soil_roughness': survey_data.get('soil_roughness', ''),
        'growth_stage': survey_data.get('growth_stage', ''),
        'water_status': survey_data.get('water_status', ''),
        'overall_health': survey_data.get('overall_health', ''),
        'visible_problems': survey_data.get('visible_problems', ''),
        'fertilizer': survey_data.get('fertilizer', ''),
        'fertilizer_type': survey_data.get('fertilizer_type', ''),
        'herbicide': survey_data.get('herbicide', ''),
        'pesticide': survey_data.get('pesticide', ''),
        'stress_events': survey_data.get('stress_events', '')
    }
    
    # Convert list to comma-separated string if needed
    if isinstance(row['visible_problems'], list):
        row['visible_problems'] = ', '.join(row['visible_problems'])
    
    # Write to CSV
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        fieldnames = list(row.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row)
    
    logger.info(f"Survey saved to CSV for user {user_id} in {location_data.get('province', 'Unknown')}")


async def save_and_upload_csv_background(
    user_id: int, 
    username: str, 
    survey_data: dict, 
    location_data: dict, 
    date_str: str
) -> None:
    """
    Background task to save survey to CSV and upload to Google Drive.
    
    This runs asynchronously so the user doesn't have to wait for these operations.
    """
    try:
        # Save to CSV (blocking I/O, run in thread pool)
        await asyncio.to_thread(
            save_survey_to_csv,
            user_id,
            username,
            survey_data,
            location_data,
            date_str
        )
        
        # Upload CSV to Google Drive using the service
        drive_service = get_drive_service()
        csv_path = 'farm_surveys.csv'
        result = await asyncio.to_thread(drive_service.upload_csv, csv_path)
        
        if result.success:
            logger.info(f"CSV uploaded to Google Drive: {result.web_link}")
        else:
            logger.warning(f"Failed to upload CSV to Google Drive: {result.error}")
            
    except Exception as e:
        logger.error(f"Background CSV save/upload error: {e}", exc_info=True)

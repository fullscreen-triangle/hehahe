"""
Data loaders for FIT, GPX, TCX, and KML files.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

import gpxpy
import numpy as np
import pandas as pd
from fitparse import FitFile
from tqdm import tqdm


class ActivityData:
    """Container for activity session data."""

    def __init__(
        self,
        timestamp: pd.Series,
        heart_rate: Optional[pd.Series] = None,
        cadence: Optional[pd.Series] = None,
        speed: Optional[pd.Series] = None,
        altitude: Optional[pd.Series] = None,
        temperature: Optional[pd.Series] = None,
        position_lat: Optional[pd.Series] = None,
        position_long: Optional[pd.Series] = None,
        vertical_oscillation: Optional[pd.Series] = None,
        ground_contact_time: Optional[pd.Series] = None,
        stride_length: Optional[pd.Series] = None,
        power: Optional[pd.Series] = None,
        metadata: Optional[Dict] = None,
    ):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.cadence = cadence
        self.speed = speed
        self.altitude = altitude
        self.temperature = temperature
        self.position_lat = position_lat
        self.position_long = position_long
        self.vertical_oscillation = vertical_oscillation
        self.ground_contact_time = ground_contact_time
        self.stride_length = stride_length
        self.power = power
        self.metadata = metadata or {}

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        data = {"timestamp": self.timestamp}

        for attr in [
            "heart_rate",
            "cadence",
            "speed",
            "altitude",
            "temperature",
            "position_lat",
            "position_long",
            "vertical_oscillation",
            "ground_contact_time",
            "stride_length",
            "power",
        ]:
            value = getattr(self, attr)
            if value is not None:
                data[attr] = value

        return pd.DataFrame(data)


class SleepData:
    """Container for sleep session data."""

    def __init__(
        self,
        timestamp: pd.Series,
        sleep_stage: pd.Series,
        heart_rate: Optional[pd.Series] = None,
        movement: Optional[pd.Series] = None,
        respiration_rate: Optional[pd.Series] = None,
        hrv: Optional[pd.Series] = None,
        metadata: Optional[Dict] = None,
    ):
        self.timestamp = timestamp
        self.sleep_stage = sleep_stage
        self.heart_rate = heart_rate
        self.movement = movement
        self.respiration_rate = respiration_rate
        self.hrv = hrv
        self.metadata = metadata or {}

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        data = {"timestamp": self.timestamp, "sleep_stage": self.sleep_stage}

        for attr in ["heart_rate", "movement", "respiration_rate", "hrv"]:
            value = getattr(self, attr)
            if value is not None:
                data[attr] = value

        return pd.DataFrame(data)


def load_fit_file(file_path: Union[str, Path], verbose: bool = False) -> ActivityData:
    """
    Load FIT file and extract time series data.

    Parameters
    ----------
    file_path : str or Path
        Path to FIT file
    verbose : bool
        Print parsing information

    Returns
    -------
    ActivityData
        Parsed activity data
    """
    file_path = Path(file_path)
    fitfile = FitFile(str(file_path))

    # Extract record messages
    records = []
    for record in fitfile.get_messages("record"):
        record_data = {}
        for field in record:
            record_data[field.name] = field.value
        records.append(record_data)

    if not records:
        raise ValueError(f"No record data found in {file_path}")

    df = pd.DataFrame(records)

    # Extract metadata from session and device info
    metadata = {}
    for message_type in ["session", "device_info", "file_id"]:
        for message in fitfile.get_messages(message_type):
            for field in message:
                metadata[f"{message_type}_{field.name}"] = field.value

    # Standardize field names
    field_mapping = {
        "timestamp": "timestamp",
        "heart_rate": "heart_rate",
        "cadence": "cadence",
        "speed": "speed",
        "enhanced_speed": "speed",
        "altitude": "altitude",
        "enhanced_altitude": "altitude",
        "temperature": "temperature",
        "position_lat": "position_lat",
        "position_long": "position_long",
        "vertical_oscillation": "vertical_oscillation",
        "stance_time": "ground_contact_time",
        "step_length": "stride_length",
        "power": "power",
    }

    extracted_data = {"timestamp": pd.to_datetime(df["timestamp"])}

    for fit_field, standard_field in field_mapping.items():
        if fit_field in df.columns and fit_field != "timestamp":
            extracted_data[standard_field] = df[fit_field]

    # Convert semicircles to degrees for position
    if "position_lat" in extracted_data:
        extracted_data["position_lat"] = extracted_data["position_lat"] * (180 / 2**31)
    if "position_long" in extracted_data:
        extracted_data["position_long"] = extracted_data["position_long"] * (180 / 2**31)

    # Convert stance time from ms to seconds
    if "ground_contact_time" in extracted_data:
        extracted_data["ground_contact_time"] = extracted_data["ground_contact_time"] / 1000.0

    activity = ActivityData(
        timestamp=extracted_data["timestamp"],
        heart_rate=extracted_data.get("heart_rate"),
        cadence=extracted_data.get("cadence"),
        speed=extracted_data.get("speed"),
        altitude=extracted_data.get("altitude"),
        temperature=extracted_data.get("temperature"),
        position_lat=extracted_data.get("position_lat"),
        position_long=extracted_data.get("position_long"),
        vertical_oscillation=extracted_data.get("vertical_oscillation"),
        ground_contact_time=extracted_data.get("ground_contact_time"),
        stride_length=extracted_data.get("stride_length"),
        power=extracted_data.get("power"),
        metadata=metadata,
    )

    if verbose:
        print(f"Loaded {file_path.name}")
        print(f"  Duration: {(activity.timestamp.max() - activity.timestamp.min())}")
        print(f"  Records: {len(activity.timestamp)}")
        fields = [
            f
            for f in [
                "heart_rate",
                "cadence",
                "speed",
                "altitude",
                "vertical_oscillation",
                "ground_contact_time",
            ]
            if getattr(activity, f) is not None
        ]
        print(f"  Available fields: {', '.join(fields)}")

    return activity


def load_gpx_file(file_path: Union[str, Path]) -> ActivityData:
    """
    Load GPX file and extract time series data.

    Parameters
    ----------
    file_path : str or Path
        Path to GPX file

    Returns
    -------
    ActivityData
        Parsed activity data
    """
    file_path = Path(file_path)

    with open(file_path, "r") as f:
        gpx = gpxpy.parse(f)

    records = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                records.append(
                    {
                        "timestamp": point.time,
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                        "elevation": point.elevation,
                    }
                )

    if not records:
        raise ValueError(f"No track data found in {file_path}")

    df = pd.DataFrame(records)

    # Compute speed from position
    if len(df) > 1:
        # Haversine distance calculation (simplified)
        lat1, lon1 = np.radians(df["latitude"].values[:-1]), np.radians(
            df["longitude"].values[:-1]
        )
        lat2, lon2 = np.radians(df["latitude"].values[1:]), np.radians(
            df["longitude"].values[1:]
        )

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        distance = 6371000 * c  # Earth radius in meters

        dt = (df["timestamp"].diff().dt.total_seconds().values[1:])
        speed = np.zeros(len(df))
        speed[1:] = distance / dt
    else:
        speed = None

    metadata = {
        "source": "gpx",
        "filename": file_path.name,
    }

    return ActivityData(
        timestamp=pd.to_datetime(df["timestamp"]),
        position_lat=df["latitude"],
        position_long=df["longitude"],
        altitude=df["elevation"] if "elevation" in df.columns else None,
        speed=pd.Series(speed) if speed is not None else None,
        metadata=metadata,
    )


def load_session_batch(
    directory: Union[str, Path],
    pattern: str = "*.fit",
    max_files: Optional[int] = None,
    verbose: bool = True,
) -> List[ActivityData]:
    """
    Load multiple session files from directory.

    Parameters
    ----------
    directory : str or Path
        Directory containing session files
    pattern : str
        File pattern to match (e.g., "*.fit", "*.gpx")
    max_files : int, optional
        Maximum number of files to load
    verbose : bool
        Show progress bar

    Returns
    -------
    List[ActivityData]
        List of loaded sessions
    """
    directory = Path(directory)
    files = sorted(directory.glob(pattern))

    if max_files:
        files = files[:max_files]

    sessions = []
    iterator = tqdm(files, desc="Loading sessions") if verbose else files

    for file_path in iterator:
        try:
            if file_path.suffix.lower() == ".fit":
                session = load_fit_file(file_path, verbose=False)
            elif file_path.suffix.lower() == ".gpx":
                session = load_gpx_file(file_path)
            else:
                continue

            sessions.append(session)
        except Exception as e:
            if verbose:
                print(f"Failed to load {file_path.name}: {e}")

    return sessions


def identify_session_type(activity: ActivityData) -> str:
    """
    Identify session type from activity data.

    Parameters
    ----------
    activity : ActivityData
        Activity session data

    Returns
    -------
    str
        Session type: "running", "cycling", "walking", "other"
    """
    if activity.cadence is None or activity.speed is None:
        return "other"

    # Heuristics based on cadence and speed
    avg_cadence = activity.cadence.median()
    avg_speed = activity.speed.median()

    if avg_cadence > 140 and avg_speed > 2.0:
        return "running"
    elif avg_cadence > 60 and avg_cadence < 120 and avg_speed > 5.0:
        return "cycling"
    elif avg_cadence < 140 and avg_speed < 2.0:
        return "walking"
    else:
        return "other"


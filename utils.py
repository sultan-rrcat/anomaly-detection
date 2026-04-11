import os
import uuid
import logging
import pandas as pd
from fastapi import Request, HTTPException
from nptdms import TdmsFile

# Session store (in-memory)
session_store = {}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger("anomaly_app")


def get_session_id(request: Request) -> str:
    """Get or create session ID."""
    session_id = request.session.get("id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session["id"] = session_id
        logger.info(f"New session created: {session_id}")
    return session_id

def detect_file_type(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    return ext
def safe_read_csv_tdms(file_path: str) -> pd.DataFrame:
    """Read CSV safely and rename channel columns if present."""
    channel_mapping = {
        "Channel 1": "LS1Q1D REF",
        "Channel 2": "LS1Q1D RDBK",
        "Channel 3": "LS2Q1D REF",
        "Channel 4": "LS2Q1D RDBK",
        "Channel 5": "LS3Q1D REF",
        "Channel 6": "LS3Q1D RDBK",
        "Channel 7": "LS4Q1D REF",
        "Channel 8": "LS4Q1D RDBK",
        "Channel 9": "LS5Q1D REF",
        "Channel 10": "LS5Q1D RDBK",
        "Channel 11": "LS6Q1D REF",
        "Channel 12": "LS6Q1D RDBK",
        "Channel 13": "LS7Q1D REF",
        "Channel 14": "LS7Q1D RDBK",
        "Channel 15": "LS8Q1D REF",
        "Channel 16": "LS8Q1D RDBK",
        "Channel 17": "LS1Q2F REF",
        "Channel 18": "LS1Q2F RDBK",
        "Channel 19": "LS2Q2F REF",
        "Channel 20": "LS2Q2F RDBK",
        "Channel 21": "LS3Q2F REF",
        "Channel 22": "LS3Q2F RDBK",
        "Channel 23": "LS4Q2F REF",
        "Channel 24": "LS4Q2F RDBK",
        "Channel 25": "LS5Q2F REF",
        "Channel 26": "LS5Q2F RDBK",
        "Channel 27": "LS6Q2F REF",
        "Channel 28": "LS6Q2F RDBK",
        "Channel 29": "LS7Q2F REF",
        "Channel 30": "LS7Q2F RDBK",
        "Channel 31": "LS8Q2F REF",
        "Channel 32": "LS8Q2F RDBK",
        "Channel 33": "LS1Q3D REF",
        "Channel 34": "LS1Q3D RDBK",
        "Channel 35": "LS2Q3D REF",
        "Channel 36": "LS2Q3D RDBK",
        "Channel 37": "LS3Q3D REF",
        "Channel 38": "LS3Q3D RDBK",
        "Channel 39": "LS4Q3D REF",
        "Channel 40": "LS4Q3D RDBK",
        "Channel 41": "LS5Q3D REF",
        "Channel 42": "LS5Q3D RDBK",
        "Channel 43": "LS6Q3D REF",
        "Channel 44": "LS6Q3D RDBK",
        "Channel 45": "LS7Q3D REF",
        "Channel 46": "LS7Q3D RDBK",
        "Channel 47": "LS8Q3D REF",
        "Channel 48": "LS8Q3D RDBK",
        "Channel 49": "SSQ4 REF",
        "Channel 50": "SSQ4 RDBK",
        "Channel 51": "DP REF",
        "Channel 52": "DP RDBK",
        "Channel 53": "SSQ5 REF",
        "Channel 54": "SSQ5 RDBK",
        "Channel 55": "SPR1",
        "Channel 56": "SPR2",
        "Channel 57": "SSSF REF",
        "Channel 58": "SSSF RDBK",
        "Channel 59": "SSSD REF",
        "Channel 60": "SSSD RDBK",
        "Channel 61": "SPR3",
        "Channel 62": "SPR4",
        "Channel 63": "SPR5",
        "Channel 64": "SPR6",
        "Channel 65": "RF1 REF",
        "Channel 66": "RF1 RDBK",
        "Channel 67": "RF2 REF",
        "Channel 68": "RF2 RDBK",
        "Channel 69": "RF3 REF",
        "Channel 70": "RF3 RDBK",
        "Channel 71": "RF4 REF",
        "Channel 72": "RF4 RDBK",
        "Channel 73": "RF5 REF",
        "Channel 74": "RF5 RDBK",
        "Channel 75": "RF6 REF",
        "Channel 76": "RF6 RDBK",
        "Channel 77": "DCCT",
        "Channel 78": "SPR7",
        "Channel 79": "ID BPI Interlock",
        "Channel 80": "MDR RF Interlock",
    }

    try:
        if detect_file_type(file_path) == '.csv':
            logger.info(f"Reading File: {file_path}")
            df = pd.read_csv(file_path)
            df = df.rename(columns=lambda col: channel_mapping.get(col, col))
            return df
        else:
            logger.info(f"Reading File: {file_path}")
            tdms_file = TdmsFile.read(file_path)
            all_data = {}
            for group in tdms_file.groups():
                for channel in group.channels():
                    all_data[channel.name] = channel[:]
            
            df = pd.DataFrame(all_data)
            df = df.rename(columns=lambda col: channel_mapping.get(col, col))

            return df

    except Exception as e:
        logger.error(f"Failed to read CSV/TDMS: {file_path} | Error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV/TDMS file: {e}")


def scale_column_values(column: str, values):
    """
    Apply scaling rules for specific channels.
    """
    if column in ("Channel 51", "DP REF", "DP RDBK"):
        return values * 100
    elif column in (
        "Channel 65", "RF1 REF", "Channel 66", "RF1 RDBK",
        "Channel 67", "RF2 REF", "Channel 68", "RF2 RDBK",
        "Channel 69", "RF3 REF", "Channel 70", "RF3 RDBK",
        "Channel 71", "RF4 REF", "Channel 72", "RF4 RDBK",
        "Channel 73", "RF5 REF", "Channel 74", "RF5 RDBK",
        "Channel 75", "RF6 REF", "Channel 76", "RF6 RDBK"
    ):
        return values * 65
    elif column in ("Channel 77", "DCCT"):
        return values * 10
    else:
        return values * 30

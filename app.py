# main app 
from fastapi import FastAPI, UploadFile, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import os
import plotly.graph_objs as go
import pandas as pd
from typing import Optional
import time
import shutil

from utils import get_session_id, safe_read_csv_tdms, session_store, scale_column_values, logger
from anomaly_methods import AnomalyDetector  # <-- unified detector

# -------------------------------
# App & Config
# -------------------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="SUPER_SECRET_KEY")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def cleanup_old_sessions():
    cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours
    for session_id in list(session_store.keys()):
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        if os.path.exists(session_dir):
            if os.path.getctime(session_dir) < cutoff_time:
                
                shutil.rmtree(session_dir)
                del session_store[session_id]
    # solution for server restart scenario
    for session_id in os.listdir(UPLOAD_DIR):
        session_dir = os.path.join(UPLOAD_DIR, session_id)

        if os.path.isdir(session_dir) and os.path.getctime(session_dir) < cutoff_time:
            logger.info(f"Deleting folder: {session_dir}")
            shutil.rmtree(session_dir)

# -------------------------------
# Routes
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "columns": None})


@app.post("/upload")
async def upload_file(request: Request, file: UploadFile):
    session_id = get_session_id(request)

    try:
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        file_path = os.path.join(session_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        session_store[session_id] = {"last_uploaded_file": file_path}
        logger.info(f"Session {session_id} uploaded file: {file.filename}")

        df = safe_read_csv_tdms(file_path)
        return JSONResponse(content={"columns": df.columns.tolist()})

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")


# -------------------------------
# Detect Graph
# -------------------------------
class DetectGraphRequest(BaseModel):
    column_name: str
    thresholdPercentile: Optional[float] = None
    kValue: Optional[int] = None
    zScoreThreshold: Optional[float] = None
    windowSize: Optional[int] = None
    lofThreshold: Optional[float] = None
    method: str

@app.post("/detect-graph")
async def detect_graph(request: Request, body: DetectGraphRequest):
    logger.info(f"Executing /detect-graph endpoint with payload: {body}")
    session_id = get_session_id(request)
    session_data = session_store.get(session_id)

    if not session_data or not os.path.exists(session_data["last_uploaded_file"]):
        raise HTTPException(status_code=400, detail="No file uploaded for this session")

    df = safe_read_csv_tdms(session_data["last_uploaded_file"])
    column = body.column_name
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found in CSV")
    
    series = pd.to_numeric(df[column], errors="coerce")
    if series.isnull().any():
        mask = series.isnull()
        null_idx = series[mask].index
        logger.info(f"NULL values in column: {column} at indexes {null_idx}. Dropping the null values.")
        series = series.dropna()

    values = series.values.astype(float)
    values = scale_column_values(column, values)

    try:
        # Build detector parameters based on method
        detector_params = {}
        
        if body.method == "knn":
            detector_params["k"] = body.kValue or 10
            detector_params["threshold_percentile"] = body.thresholdPercentile or 99.99
        elif body.method == "isolation_forest":
            detector_params["threshold_percentile"] = body.thresholdPercentile or 99.99
        elif body.method in ["zscore", "rolling_zscore"]:
            detector_params["threshold"] = body.zScoreThreshold or 3.0
            if body.method == "rolling_zscore":
                detector_params["window"] = body.windowSize or 50
        elif body.method == "lof":
            detector_params["k"] = body.kValue or 20
            detector_params["lof_threshold"] = body.lofThreshold or 1.5
            detector_params["threshold_percentile"] = body.thresholdPercentile or 99.99
        elif body.method == "minmax":
            pass
            
        detector = AnomalyDetector(method=body.method, **detector_params)
        flags = detector.detect(values)
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return {"error": "Anomaly detection failed", "anomalies": 0}

    # Plot
    trace1 = go.Scatter(x=list(range(len(values))), y=values, mode="lines", name="Data")
    trace2 = go.Scatter(
        x=[i for i, f in enumerate(flags) if f],
        y=[values[i] for i, f in enumerate(flags) if f],
        mode="markers", marker=dict(color="red", size=6), name="Anomalies"
    )

    fig = go.Figure(data=[trace1, trace2])
    fig.update_layout(title=f"{int(flags.sum())} Anomalies in {column} ({body.method.upper()})", template="plotly_white")

    return {"graph_json": fig.to_json(), "anomalies": int(flags.sum())}


# -------------------------------
# Run All Columns
# -------------------------------
class RunAllRequest(BaseModel):
    thresholdPercentile: Optional[float] = None
    kValue: Optional[int] = None
    zScoreThreshold: Optional[float] = None
    lofThreshold: Optional[float] = None
    windowSize: Optional[int] = None
    method: str


@app.post("/run-all")
async def run_all(request: Request, body: RunAllRequest):
    logger.info(f"Executing /run-all endpoint with payload: {body}")
    session_id = get_session_id(request)
    session_data = session_store.get(session_id)

    if not session_data or not os.path.exists(session_data["last_uploaded_file"]):
        raise HTTPException(status_code=400, detail="No file uploaded for this session")

    df = safe_read_csv_tdms(session_data["last_uploaded_file"])
    column_names = df.columns.tolist()

    anomaly_results = []
    for column in column_names:
        try:
            series = pd.to_numeric(df[column], errors="coerce")
            if series.isnull().any():
                mask = series.isnull()
                null_idx = series[mask].index
                logger.info(f"Null value in column: {column} at index {null_idx}. Dropping null values.")
                series = series.dropna()

            values = series.values.astype(float)
            values = pd.to_numeric(df[column], errors="coerce").dropna().values.astype(float)
            if values.size == 0:
                continue

            values = scale_column_values(column, values)
            
            # Build detector parameters based on method
            detector_params = {}
            
            if body.method in ["knn"]:
                detector_params["k"] = body.kValue or 10
                detector_params["threshold_percentile"] = body.thresholdPercentile or 95
            elif body.method == "isolation_forest":
                detector_params["threshold_percentile"] = body.thresholdPercentile or 95
            elif body.method in ["zscore", "rolling_zscore"]:
                detector_params["threshold"] = body.zScoreThreshold or 3.0
                if body.method == "rolling_zscore":
                    detector_params["window"] = body.windowSize or 50
            elif body.method == "lof":
                detector_params["k"] = body.kValue or 20
                detector_params["lof_threshold"] = body.lofThreshold or 1.5
                detector_params["threshold_percentile"] = body.thresholdPercentile or 99.99

            # logger.info(f"body.RunAllRequest: {body}")
            detector = AnomalyDetector(method=body.method, **detector_params)
            flags = detector.detect(values)

            anomaly_count = int(flags.sum())
            # anomaly_count = flags.size
            if anomaly_count > 0:
                anomaly_results.append({"column": column, "count": anomaly_count})

        except Exception as col_err:
            logger.warning(f"Skipping column {column} due to error: {col_err}")

    logger.info(f"Anomaly Result: {anomaly_results}")

    anomaly_results.sort(key=lambda x: x["count"], reverse=True)
    session_data["anomaly_columns"] = [r["column"] for r in anomaly_results]

    return {"status": "file generated", "anomaly_columns": anomaly_results}


# -------------------------------
# Change Color (for frontend highlighting)
# -------------------------------
@app.get("/change-color")
async def change_color(request: Request):
    session_id = get_session_id(request)
    session_data = session_store.get(session_id)

    if not session_data or "anomaly_columns" not in session_data:
        return {"anomaly_columns": []}
    
    return {"anomaly_columns": session_data["anomaly_columns"]}


#---------------------------------
# At start up
#---------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("Starting the Anomaly Detection Application.")
    await cleanup_old_sessions()

#------------------------------
# At shutdown
#------------------------------
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the Anomaly Detection Application.")
    pass

@app.get("/health")
async def health_check():
    return {"status": "ok"}
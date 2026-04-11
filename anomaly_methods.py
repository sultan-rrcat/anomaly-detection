# anomaly methods 
import cupy as cp
import pandas as pd
from cuml.neighbors import NearestNeighbors
from fastapi import HTTPException
import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from utils import logger

class AnomalyDetector:
    def __init__(self, method="knn", **kwargs):
        """
        method: str
            - "knn"
            - "zscore"
            - "rolling_zscore"
            - "lof"
            - "isolation_forest"
        kwargs: method-specific parameters
        """
        self.method = method
        self.params = kwargs

    def detect(self, values):
        if self.method == "knn":
            return self._detect_knn(values)
        elif self.method == "zscore":
            return self._detect_zscore(values)
        elif self.method == "rolling_zscore":
            return self._detect_rolling_zscore(values)
        elif self.method == "lof":
            return self._detect_lof(values)
        elif self.method == "isolation_forest":
            return self._detect_isolation_forest(values)
        elif self.method == "minmax":
            return self._detect_min_max(values)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    # -------------------------------
    # Methods
    # -------------------------------

    def _detect_knn(self, values):
        k = self.params.get("k", 10)
        threshold_percentile = self.params.get("threshold_percentile", 95)

        if values.size < k:
            raise HTTPException(status_code=400, detail=f"Not enough data points ({values.size}) for k={k}")

        X = cp.array(values).reshape(-1, 1)
        knn = NearestNeighbors(n_neighbors=k)
        knn.fit(X)
        distances, _ = knn.kneighbors(X)
        kth = distances[:, -1]
        threshold = cp.percentile(kth, threshold_percentile)
        flags = (kth > threshold).get()

        # cleanup GPU memory
        del X, kth
        cp.get_default_memory_pool().free_all_blocks()

        return flags

    def _detect_zscore(self, values):
        threshold = self.params.get("threshold", 3.0)
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return np.zeros(len(values), dtype=bool)
        z_scores = (values - mean) / std
        return np.abs(z_scores) > threshold

    def _detect_rolling_zscore(self, values):
        threshold = self.params.get("threshold", 3.0)
        window = self.params.get("window", 50)
        
        if len(values) < window:
            # Fallback to regular z-score if not enough data
            return self._detect_zscore(values)
            
        series = pd.Series(values)
        rolling_mean = series.rolling(window=window, min_periods=1).mean()
        rolling_std = series.rolling(window=window, min_periods=1).std()
        
        # Handle cases where rolling std is 0
        rolling_std = rolling_std.fillna(0)
        rolling_std = rolling_std.replace(0, np.nan)
        
        z_scores = (series - rolling_mean) / rolling_std
        z_scores = z_scores.fillna(0)  # Replace NaN with 0 (not anomalous)
        
        return np.abs(z_scores) > threshold

    def _detect_min_max(self, values):
        min = np.min(values)
        max = np.max(values)
        return (values == min) | (values == max)

    def _detect_lof(self, values):
        k = self.params.get("k", 20)  # Default k is 20
        threshold_percentile = self.params.get("threshold_percentile", 99.99)
        min_lof_threshold = self.params.get("lof_threshold", 1.5)  
        # LOF ~ 1 = normal, >1.5 = likely anomaly

        if values.size <= k:
            raise HTTPException(status_code=400, detail=f"Not enough data points ({values.size}) for n_neighbors={k}")

        # Reshape for sklearn
        X = values.reshape(-1, 1)

        # Fit LOF model
        lof = LocalOutlierFactor(n_neighbors=k)
        lof.fit(X)

        # LOF scores (higher = more anomalous)
        lof_scores = -lof.negative_outlier_factor_

        # Compute threshold from percentile
        percentile_threshold = np.percentile(lof_scores, threshold_percentile)

        # Final threshold = max(percentile, minimum LOF to be considered anomaly)
        threshold = max(percentile_threshold, min_lof_threshold)

        # Flag points only if score exceeds threshold
        flags = lof_scores > threshold

        return flags


    def _detect_isolation_forest(self, values):
        threshold_percentile = self.params.get("threshold_percentile", 95)
        # Convert percentile to the contamination fraction sklearn expects
        contamination = (100 - threshold_percentile) / 100.0
        
        # Ensure contamination is within scikit-learn's valid range (0, 0.5]
        contamination = max(0.001, min(0.5, contamination))

        if values.size < 10:
            raise HTTPException(status_code=400, detail=f"Not enough data points ({values.size}) for Isolation Forest")

        # Use scikit-learn's Isolation Forest
        X = values.reshape(-1, 1)
        iso_forest = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        
        # fit_predict returns -1 for outliers, 1 for inliers
        outlier_flags = iso_forest.fit_predict(X)
        
        flags = (outlier_flags == -1)
        return flags
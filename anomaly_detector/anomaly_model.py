import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies(csv_path="anomaly_detector/sample_metrics.csv"):
    df = pd.read_csv(csv_path)
    features = ["cpu_percent", "ram_percent", "disk_usage"]
    model = IsolationForest(contamination=0.1, random_state=42)
    df["anomaly"] = model.fit_predict(df[features])
    df["anomaly_label"] = df["anomaly"].map({1: "Normal", -1: "Anomaly"})
    return df

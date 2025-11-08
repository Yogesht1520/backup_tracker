import matplotlib.pyplot as plt
from anomaly_model import detect_anomalies

def plot_anomalies():
    df = detect_anomalies()
    plt.figure(figsize=(10,5))
    plt.plot(df["cpu_percent"], label="CPU Usage", marker="o")
    plt.scatter(df.index[df["anomaly"] == -1], df["cpu_percent"][df["anomaly"] == -1],
                color="red", label="Anomaly")
    plt.title("CPU Usage Anomaly Detection")
    plt.xlabel("Sample")
    plt.ylabel("CPU %")
    plt.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_anomalies()

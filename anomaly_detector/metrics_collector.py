import socketio
import psutil, time, datetime

sio = socketio.Client()

@sio.event
def connect():
    print("✅ Connected to Flask server!")

@sio.event
def disconnect():
    print("❌ Disconnected from server")

def collect_metrics():
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # ✅ Emit only if connected
            if sio.connected:
                sio.emit('metrics_update', {
                    'timestamp': timestamp,
                    'cpu': cpu,
                    'ram': ram,
                    'disk': disk
                })
                print(f"📡 Sent metrics — CPU: {cpu}%, RAM: {ram}%, Disk: {disk}%")
            else:
                print("⚠️ Not connected — skipping emit")

        except Exception as e:
            print("⚠️ Error sending metrics:", e)

        time.sleep(5)  # send every 5 seconds

if __name__ == "__main__":
    print("📊 Starting extended metrics collector...")

    while True:
        try:
            # Try to connect to Flask app
            sio.connect("http://127.0.0.1:5050", wait_timeout=5)
            collect_metrics()
        except socketio.exceptions.ConnectionError:
            print("❌ Cannot connect to Flask server — retrying in 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Metrics collection stopped manually.")
            break
        except Exception as e:
            print("Unexpected error:", e)
            time.sleep(5)

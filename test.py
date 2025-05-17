import sys
import platform
import psutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QTabWidget
)
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SystemMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitor - Detailed Info with Graphs")
        self.resize(900, 700)

        # Dark style
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #eeeeee;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 12pt;
            }
            QTabWidget::pane {
                border: 2px solid #444444;
                border-radius: 8px;
                margin: 5px;
                padding: 5px;
            }
            QTabBar::tab {
                background: #333333;
                border: 1px solid #555555;
                border-bottom-color: #222222;
                padding: 8px 15px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #00aaff;
                color: white;
                font-weight: bold;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #444444;
                padding: 5px;
            }
            QLabel {
                padding: 5px;
            }
        """)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Tab 1: System Info + Graphs
        self.tab_system = QWidget()
        self.tabs.addTab(self.tab_system, "System Info")
        self.tab_system_layout = QVBoxLayout()
        self.tab_system.setLayout(self.tab_system_layout)

        # Info labels
        self.label_os = QLabel()
        self.label_cpu = QLabel()
        self.label_ram = QLabel()
        self.label_disk = QLabel()
        self.label_battery = QLabel()
        self.label_network = QLabel()

        self.tab_system_layout.addWidget(self.label_os)
        self.tab_system_layout.addWidget(self.label_cpu)
        self.tab_system_layout.addWidget(self.label_ram)
        self.tab_system_layout.addWidget(self.label_disk)
        self.tab_system_layout.addWidget(self.label_battery)
        self.tab_system_layout.addWidget(self.label_network)

        # Graph setup
        self.figure = Figure(figsize=(8,3))
        self.canvas = FigureCanvas(self.figure)
        self.tab_system_layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_ylim(0, 100)
        self.ax.set_title("CPU & RAM Usage Over Time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Usage (%)")

        # Data containers for graph
        self.cpu_data = []
        self.ram_data = []
        self.time_data = []
        self.wifi_speed_data = []
        self.max_points = 60
        self.counter = 0

        # Tab 2: Processes
        self.tab_processes = QWidget()
        self.tabs.addTab(self.tab_processes, "Processes")
        self.tab_processes_layout = QVBoxLayout()
        self.tab_processes.setLayout(self.tab_processes_layout)

        self.process_list = QListWidget()
        self.tab_processes_layout.addWidget(self.process_list)

        # Previous wifi data for speed calc
        self.prev_wifi_sent = 0
        self.prev_wifi_recv = 0

        # Timer to update info & graph every 1 second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000)

        self.update_info()

    def update_info(self):
        # Update system info
        uname = platform.uname()
        os_info = f"System: {uname.system} {uname.release} ({uname.version})\nProcessor: {uname.processor}"
        self.label_os.setText(os_info)

        cpu_percent = psutil.cpu_percent()
        self.label_cpu.setText(f"CPU Usage: {cpu_percent}%")

        mem = psutil.virtual_memory()
        ram_info = f"RAM Usage: {mem.percent}% ({mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB)"
        self.label_ram.setText(ram_info)

        disk = psutil.disk_usage('/')
        disk_info = f"Disk Usage (C:): {disk.percent}% ({disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB)"
        self.label_disk.setText(disk_info)

        battery = psutil.sensors_battery()
        if battery:
            plugged = "Plugged In" if battery.power_plugged else "Not Plugged"
            batt_info = f"Battery: {battery.percent}% - {plugged}"
        else:
            batt_info = "Battery: Not Available"
        self.label_battery.setText(batt_info)

        # Update network info focused on WiFi interface
        net_if_stats = psutil.net_if_stats()
        wifi_interface = None
        for iface in net_if_stats:
            if "wi-fi" in iface.lower() or "wireless" in iface.lower():
                wifi_interface = iface
                break

        if wifi_interface and net_if_stats[wifi_interface].isup:
            counters = psutil.net_io_counters(pernic=True)[wifi_interface]
            if self.prev_wifi_sent == 0:
                self.prev_wifi_sent = counters.bytes_sent
                self.prev_wifi_recv = counters.bytes_recv
                wifi_sent_speed = 0
                wifi_recv_speed = 0
            else:
                wifi_sent_speed = (counters.bytes_sent - self.prev_wifi_sent) / 1024  # KB/s
                wifi_recv_speed = (counters.bytes_recv - self.prev_wifi_recv) / 1024
                self.prev_wifi_sent = counters.bytes_sent
                self.prev_wifi_recv = counters.bytes_recv

            wifi_info = f"WiFi Interface: {wifi_interface} | Upload: {wifi_sent_speed:.2f} KB/s | Download: {wifi_recv_speed:.2f} KB/s"
        else:
            wifi_info = "WiFi Interface: Not Connected or Not Found"

        self.label_network.setText(wifi_info)

        # Update processes list
        self.process_list.clear()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                item = QListWidgetItem(f"PID: {proc.info['pid']} - {proc.info['name']}")
                self.process_list.addItem(item)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Update graph data
        if len(self.cpu_data) >= self.max_points:
            self.cpu_data.pop(0)
            self.ram_data.pop(0)
            self.time_data.pop(0)
            self.wifi_speed_data.pop(0)

        self.cpu_data.append(cpu_percent)
        self.ram_data.append(mem.percent)
        self.time_data.append(self.counter)
        self.wifi_speed_data.append(wifi_recv_speed)  # نرسم سرعة التنزيل

        self.counter += 1

        self.ax.clear()
        max_y = max(100, max(self.wifi_speed_data + [0]) + 10)
        self.ax.set_ylim(0, max_y)
        self.ax.set_title("CPU & RAM Usage and WiFi Download Speed Over Time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Usage (%) / Speed (KB/s)")
        self.ax.plot(self.time_data, self.cpu_data, label="CPU (%)", color="#00aaff")
        self.ax.plot(self.time_data, self.ram_data, label="RAM (%)", color="#ffaa00")
        self.ax.plot(self.time_data, self.wifi_speed_data, label="WiFi Download Speed (KB/s)", color="#00ff00")
        self.ax.legend()
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemMonitor()
    window.show()
    sys.exit(app.exec_())

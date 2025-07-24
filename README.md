# RPi5 Multi-Camera RTSP Server

A high-performance RTSP streaming server designed specifically for the Raspberry Pi 5, supporting multiple camera sources including local libcamera devices and remote RTSP streams. This project provides a unified streaming solution optimized for the RPi5's ARM64 architecture and software encoding capabilities.

## 🎯 Features

- **Multi-Camera Support**: Stream from up to 3 cameras simultaneously
- **Mixed Source Types**: Combine local libcamera devices with remote RTSP streams
- **RPi5 Optimized**: Specifically tuned for Raspberry Pi 5's CPU and memory architecture
- **Software Encoding**: Utilizes efficient x264 software encoding (no hardware encoder dependency)
- **Stream Passthrough**: Smart proxy mode for remote streams to minimize CPU usage
- **Real-time Monitoring**: Comprehensive logging and error handling for all pipeline states
- **Multi-client Ready**: Shared streams allow multiple concurrent viewers
- **Low Latency**: Optimized for real-time streaming applications

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Arducam 0     │    │                  │    │   RTSP Client   │
│   (libcamera)   ├────┤                  ├────┤   Port :8555    │
└─────────────────┘    │                  │    └─────────────────┘
                       │   RPi5 RTSP      │
┌─────────────────┐    │   Server         │    ┌─────────────────┐
│   Arducam 1     │    │                  │    │   RTSP Client   │
│   (libcamera)   ├────┤  - Software      ├────┤   Port :8555    │
└─────────────────┘    │    Encoding      │    └─────────────────┘
                       │  - Stream Proxy   │
┌─────────────────┐    │  - Multi-client  │    ┌─────────────────┐
│  Remote Camera  │    │                  │    │   RTSP Client   │
│  (RTSP Stream)  ├────┤                  ├────┤   Port :8555    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 Requirements

### Hardware
- **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- **MicroSD Card**: Class 10 or better, 32GB+ recommended
- **Camera Modules**: 
  - 2x Arducam IMX477 modules (or compatible libcamera devices)
  - 1x Remote IP camera with RTSP support
- **Network**: Ethernet or WiFi connection
- **Power Supply**: Official RPi5 power supply (27W recommended)

### Software
- **Raspberry Pi OS**: Bookworm (64-bit) or later
- **Python**: 3.9+ (included with Raspberry Pi OS)
- **GStreamer**: 1.20+ with RTSP server support
- **libcamera**: Latest version (for camera support)

## 🚀 Installation

### 1. System Setup

Update your Raspberry Pi 5 system:
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Dependencies

Install GStreamer and related packages:
```bash
sudo apt install -y \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gst-rtsp-server-1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    libcamera-apps \
    libcamera-dev
```

### 3. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/rpi5-rtsp-server.git
cd rpi5-rtsp-server
```

### 4. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

### 5. Configure Camera Names

Check your camera device names:
```bash
libcamera-hello --list-cameras
```

Update the camera names in `rtsp_server.py` if they differ from:
- Camera 0: `/base/axi/pcie@1000120000/rp1/i2c@88000/imx477@1a`
- Camera 1: `/base/axi/pcie@1000120000/rp1/i2c@80000/imx477@1a`

### 6. Configure Remote Camera

Update the remote RTSP URL in `rtsp_server.py` line 105:
```python
'rtspsrc location=rtsp://YOUR_CAMERA_IP:PORT/stream_path latency=0 buffer-mode=1 ! '
```

## 🎮 Usage

### Basic Operation

Start the RTSP server:
```bash
python3 rtsp_server.py
```

The server will start and display:
```
Stream for Camera 0 configured at rtsp://0.0.0.0:8555/cam0
Stream for Camera 1 configured at rtsp://0.0.0.0:8555/cam1
Stream for Camera 2 (remote proxy) configured at rtsp://0.0.0.0:8555/cam2

RTSP server started. Access streams from other devices using:
  rtsp://YOUR_PI_IP:8555/cam0  (Local Arducam 0)
  rtsp://YOUR_PI_IP:8555/cam1  (Local Arducam 1)
  rtsp://YOUR_PI_IP:8555/cam2  (Remote camera proxy)
```

### Stream URLs

Replace `YOUR_PI_IP` with your Raspberry Pi 5's IP address:

- **Camera 0**: `rtsp://YOUR_PI_IP:8555/cam0`
- **Camera 1**: `rtsp://YOUR_PI_IP:8555/cam1`
- **Camera 2**: `rtsp://YOUR_PI_IP:8555/cam2`

### Viewing Streams

#### VLC Media Player
1. Open VLC
2. Go to Media → Open Network Stream
3. Enter the RTSP URL (e.g., `rtsp://192.168.1.100:8555/cam0`)

#### FFplay
```bash
ffplay rtsp://YOUR_PI_IP:8555/cam0
```

#### GStreamer
```bash
gst-launch-1.0 rtspsrc location=rtsp://YOUR_PI_IP:8555/cam0 ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink
```

### Running as a Service

Create a systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/rtsp-server.service
```

Add the following content:
```ini
[Unit]
Description=RPi5 RTSP Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rpi5-rtsp-server
ExecStart=/usr/bin/python3 /home/pi/rpi5-rtsp-server/rtsp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable rtsp-server.service
sudo systemctl start rtsp-server.service
sudo systemctl status rtsp-server.service
```

## ⚙️ Configuration

### Stream Settings

The server is configured with the following default settings:

| Parameter | Camera 0 & 1 | Camera 2 (Remote) |
|-----------|---------------|-------------------|
| Resolution | 1280x720 | Passthrough |
| Framerate | 30 FPS | Passthrough |
| Bitrate | 2000 kbps | Passthrough (1500 kbps) |
| Encoding | x264 (software) | No re-encoding |
| Profile | Baseline | Passthrough |

### Performance Tuning

#### For High-Performance Applications:
```python
# In rtsp_server.py, modify encoder settings:
'x264enc tune=zerolatency bitrate=3000 speed-preset=fast key-int-max=30 threads=3 ! '
```

#### For Lower CPU Usage:
```python
# Reduce resolution and bitrate:
'video/x-raw,width=960,height=540,framerate=25/1 ! '
'x264enc tune=zerolatency bitrate=1000 speed-preset=ultrafast key-int-max=50 threads=1 ! '
```

#### For Battery-Powered Operation:
```python
# Ultra-low power settings:
'video/x-raw,width=640,height=480,framerate=15/1 ! '
'x264enc tune=zerolatency bitrate=500 speed-preset=ultrafast key-int-max=60 threads=1 ! '
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Camera Not Detected
```bash
# Check if cameras are detected
libcamera-hello --list-cameras

# If no cameras found, check connections and power
sudo dmesg | grep -i camera
```

#### 2. High CPU Usage
- Reduce encoder threads: `threads=1`
- Use faster preset: `speed-preset=ultrafast`
- Lower resolution or bitrate
- Check system temperature: `vcgencmd measure_temp`

#### 3. Stream Drops or Freezes
- Check network stability
- Increase buffer sizes in queue elements
- Monitor system resources: `htop`
- Check for thermal throttling

#### 4. Remote Camera Connection Issues
```bash
# Test remote stream directly
gst-launch-1.0 rtspsrc location=rtsp://REMOTE_IP:PORT/stream ! fakesink

# Check network connectivity
ping REMOTE_CAMERA_IP
```

### Debugging

Enable verbose GStreamer debugging:
```bash
export GST_DEBUG=3
python3 rtsp_server.py
```

Monitor system resources:
```bash
# CPU and memory usage
htop

# Temperature monitoring
watch -n 1 vcgencmd measure_temp

# Network activity
sudo netstat -tlnp | grep :8555
```

### Log Analysis

The server provides comprehensive logging:
- **Pipeline Creation**: Successful/failed pipeline initialization
- **Runtime Errors**: GStreamer pipeline errors with debug info
- **State Changes**: Pipeline state transitions
- **Warnings**: Non-fatal issues that might affect performance

## 🚀 Performance Optimization

### System-Level Optimizations

#### 1. GPU Memory Split
```bash
# Add to /boot/config.txt
gpu_mem=128
```

#### 2. CPU Governor
```bash
# Set performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### 3. Network Optimization
```bash
# Increase network buffers
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
```

#### 4. I/O Priority
```bash
# Run with higher I/O priority
sudo ionice -c 1 -n 4 python3 rtsp_server.py
```

## 📊 Monitoring and Metrics

### Built-in Monitoring

The server includes built-in monitoring that logs:
- Pipeline state changes
- Error conditions and recovery
- Buffer underruns/overruns
- Network connection status

### External Monitoring

Monitor system performance:
```bash
# Real-time system stats
iostat -x 1

# Network statistics
ss -tuln | grep :8555

# Process-specific monitoring
pidstat -p $(pgrep -f rtsp_server.py) 1
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/rpi5-rtsp-server.git
cd rpi5-rtsp-server

# Create development branch
git checkout -b develop

# Install development dependencies
pip3 install -r requirements-dev.txt
```

### Coding Standards

- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes
- Include unit tests for new features
- Update documentation for any changes

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Raspberry Pi Foundation** for the excellent RPi5 hardware
- **GStreamer Project** for the powerful multimedia framework
- **libcamera Project** for camera support on RPi5
- **Arducam** for high-quality camera modules
- **Community Contributors** who helped test and improve this project

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/rpi5-rtsp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/rpi5-rtsp-server/discussions)
- **Wiki**: [Project Wiki](https://github.com/YOUR_USERNAME/rpi5-rtsp-server/wiki)

## 🔄 Changelog

### v1.0.0 (2025-01-XX)
- Initial release
- Support for 3 concurrent camera streams
- RPi5-optimized software encoding
- Remote RTSP stream proxy functionality
- Comprehensive error handling and logging

---

**Made with ❤️ for the Raspberry Pi 5 community**

#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

# Custom Media Factory to add logging for pipeline creation and state changes
class MyRTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def do_create_element(self, url):
        """
        This method is called by the RTSP server to create the GStreamer pipeline
        based on the launch string set by set_launch().
        We override it to add error handling and bus watching for runtime events.
        """
        try:
            # Gst.parse_launch is used to parse the pipeline string.
            # If the pipeline string is invalid, it will raise a GLib.Error.
            pipeline = Gst.parse_launch(self.get_launch())
            if pipeline:
                print(f"Successfully created pipeline for {url}: {self.get_launch()}")
                # Add a bus watch to the pipeline to catch runtime errors, warnings, and state changes
                bus = pipeline.get_bus()
                bus.add_signal_watch()
                # Connect the bus message handler
                bus.connect("message", self._on_bus_message, url)
            else:
                # This case should ideally be caught by the GLib.Error, but added for robustness.
                print(f"Failed to create pipeline for {url}. Pipeline string might be invalid or empty: {self.get_launch()}")
            return pipeline
        except GLib.Error as e:
            # Catch GStreamer parsing errors and print them
            print(f"ERROR: GStreamer pipeline creation failed for {url}: {e}. Pipeline string: {self.get_launch()}")
            return None

    def _on_bus_message(self, bus, message, url):
        """
        Callback function to handle messages from the GStreamer bus.
        Logs errors, warnings, end-of-stream, and pipeline state changes.
        """
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"RTSP PIPELINE ERROR for {url}: {err.message} (debug: {debug})")
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            print(f"RTSP PIPELINE WARNING for {url}: {warn.message} (debug: {debug})")
        elif t == Gst.MessageType.EOS:
            print(f"RTSP PIPELINE EOS (End-Of-Stream) reached for {url}")
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            # Only log state changes for the main pipeline, not individual elements
            if message.src == bus.get_pipeline():
                print(f"RTSP PIPELINE STATE_CHANGED for {url}: {old_state.get_name()} -> {new_state.get_name()}")

class RTSPServer:
    def __init__(self):
        # Initialize GStreamer. This must be called before using any GStreamer functions.
        Gst.init(None)

        # Create a new RTSP server instance
        self.server = GstRtspServer.RTSPServer()
        # Set the service port for the RTSP server. Changed to 8555 as in your original code.
        self.server.set_property('service', '8555')
        # Set the server to listen on all available network interfaces (0.0.0.0)
        self.server.set_property('address', '0.0.0.0')

        # Get the mount points object from the server, where factories are added
        mount_points = self.server.get_mount_points()

        # --- Factory for Camera 0 (Original Camera) ---
        # Camera name for the first Arducam, as provided by you
        cam0_name = '/base/axi/pcie@1000120000/rp1/i2c@88000/imx477@1a'
        # Define the GStreamer pipeline for Camera 0.
        # Optimized for RPi5 with software encoding (no hardware encoder available)
        pipeline_cam0 = (
            f'libcamerasrc camera-name={cam0_name} ! '
            'videoconvert ! '
            'video/x-raw,format=I420 ! ' # Specify I420 format for compatibility
            'videoscale ! '
            'video/x-raw,width=1280,height=720,framerate=30/1 ! ' # Specify desired resolution and framerate
            'videoflip video-direction=2 ! '  # Correct 180-degree rotation (video-direction=2 for 180 deg)
            'queue max-size-buffers=100 max-size-time=500000000 ! ' # Add queue with 0.5 second buffer
            'x264enc tune=zerolatency bitrate=2000 speed-preset=veryfast key-int-max=30 threads=2 ! ' # Optimized for RPi5 CPU
            'video/x-h264,profile=baseline ! '
            'queue max-size-buffers=100 max-size-time=500000000 ! ' # Add queue with 0.5 second buffer
            'rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory_cam0 = MyRTSPMediaFactory() # Use our custom factory for better error logging
        factory_cam0.set_launch(pipeline_cam0)
        factory_cam0.set_shared(True) # Allows multiple clients to connect to the same stream
        mount_points.add_factory('/cam0', factory_cam0)
        print(f"Stream for Camera 0 configured at rtsp://0.0.0.0:8555/cam0")

        # --- Factory for Camera 1 (Second Arducam) ---
        # Camera name for the second Arducam, as provided by you
        cam1_name = '/base/axi/pcie@1000120000/rp1/i2c@80000/imx477@1a'
        # Define the GStreamer pipeline for Camera 1, similar to Camera 0
        # Optimized for RPi5 with software encoding (no hardware encoder available)
        pipeline_cam1 = (
            f'libcamerasrc camera-name={cam1_name} ! '
            'videoconvert ! '
            'video/x-raw,format=I420 ! ' # Specify I420 format
            'videoscale ! '
            'video/x-raw,width=1280,height=720,framerate=30/1 ! ' # Specify desired resolution and framerate
            'videoflip video-direction=2 ! '  # Correct 180-degree rotation (video-direction=2 for 180 deg)
            'queue max-size-buffers=100 max-size-time=500000000 ! ' # Add queue with 0.5 second buffer
            'x264enc tune=zerolatency bitrate=2000 speed-preset=veryfast key-int-max=30 threads=2 ! ' # Optimized for RPi5 CPU
            'video/x-h264,profile=baseline ! '
            'queue max-size-buffers=100 max-size-time=500000000 ! ' # Add queue with 0.5 second buffer
            'rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory_cam1 = MyRTSPMediaFactory() # Use our custom factory
        factory_cam1.set_launch(pipeline_cam1)
        factory_cam1.set_shared(True)
        mount_points.add_factory('/cam1', factory_cam1)
        print(f"Stream for Camera 1 configured at rtsp://0.0.0.0:8555/cam1")

        # --- Factory for Camera 2 (Remote RTSP Stream) ---
        # Define the GStreamer pipeline for Camera 2 (remote RTSP stream proxy)
        # This will receive the existing H.264 stream and repackage it without re-encoding
        pipeline_cam2 = (
            'rtspsrc location=rtsp://192.168.144.25:8554/main.264 latency=0 buffer-mode=1 ! '
            'rtph264depay ! '
            'h264parse ! '
            'queue max-size-buffers=100 max-size-time=500000000 ! ' # Add queue with 0.5 second buffer
            'rtph264pay config-interval=1 name=pay0 pt=96'
        )
        factory_cam2 = MyRTSPMediaFactory() # Use our custom factory
        factory_cam2.set_launch(pipeline_cam2)
        factory_cam2.set_shared(True)
        mount_points.add_factory('/cam2', factory_cam2)
        print(f"Stream for Camera 2 (remote proxy) configured at rtsp://0.0.0.0:8555/cam2")

        # Attach the server to the default GLib main context.
        # This makes the server active and ready to accept connections.
        self.server.attach(None)
        print("\nRTSP server started. Access streams from other devices using:")
        print("  rtsp://YOUR_PI_IP:8555/cam0  (Local Arducam 0)")
        print("  rtsp://YOUR_PI_IP:8555/cam1  (Local Arducam 1)")
        print("  rtsp://YOUR_PI_IP:8555/cam2  (Remote camera proxy)")
        print("\nOptimizations for RPi5:")
        print("- Software encoding only (no hardware encoder available)")
        print("- Reduced thread count (2 per encoder) to balance CPU load")
        print("- Changed speed-preset to 'veryfast' for better performance")
        print("- Camera 2 uses stream passthrough (no re-encoding)")

if __name__ == '__main__':
    server = RTSPServer()
    # Create a GLib main loop to keep the server running and processing events
    loop = GLib.MainLoop()
    try:
        loop.run() # Start the main loop
    except KeyboardInterrupt:
        # Handle Ctrl+C to gracefully stop the server
        print("\nStopping RTSP server.")
        loop.quit() # Exit the main loop

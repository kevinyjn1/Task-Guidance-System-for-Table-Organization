"""
Main Application
Entry point for the Table Organization Guidance System.
"""

import os
# Suppress Qt font directory warnings from OpenCV
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts.warning=false"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import cv2
import argparse
import sys
from pathlib import Path
import numpy as np

try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    print("Warning: pyrealsense2 not available. Standard webcam will be used.")

from perception import SurfaceTracker, HandTracker, HybridObjectDetector
from state_manager import StateManager
from visualization import Renderer


class TableGuidanceSystem:
    """
    Main system integrating perception, state management, and visualization.
    """

    def __init__(self, config_path, use_realsense=True):
        """
        Initialize the table guidance system.

        Args:
            config_path: Path to procedure configuration JSON
            use_realsense: Use RealSense camera if available (default: True)
        """
        print("Initializing Table Organization Guidance System...")

        # Initialize components
        self.surface_tracker = SurfaceTracker(marker_ids=[0, 1, 2, 3])

        # Use Hybrid detector (YOLO for bottle, color-based for tape/blocks)
        print("Loading Hybrid object detector...")

        # Color-based detection config for tape and blocks
        # Calibrated for: BLUE masking tape + Yellow/White/Orange blocks
        color_objects = {
            'tape': {
                'color_ranges': [
                    # Blue masking tape (dark blue roll)
                    (np.array([90, 80, 50]), np.array([130, 255, 255]))
                ],
                'min_area': 500,      # Increased for tape roll
                'max_area': 50000,
                'aspect_ratio_range': (0.5, 2.5)  # Circular roll or rectangular
            },
            'block': {
                'color_ranges': [
                    # Yellow blocks
                    (np.array([20, 100, 100]), np.array([35, 255, 255])),
                    # Orange blocks
                    (np.array([5, 100, 100]), np.array([20, 255, 255])),
                    # White blocks (low saturation)
                    (np.array([0, 0, 180]), np.array([180, 40, 255]))
                ],
                'min_area': 200,      # Small cubes
                'max_area': 15000,
                'aspect_ratio_range': (0.5, 2.0)  # Roughly square/cubic
            }
        }

        self.object_detector = HybridObjectDetector(
            yolo_objects=['bottle'],
            color_objects=color_objects
        )

        self.hand_tracker = HandTracker(max_hands=2)
        print(f"Hand tracking enabled: {self.hand_tracker.enabled}")
        self.state_manager = StateManager(config_path)
        self.renderer = Renderer()

        # Initialize camera (RealSense or standard webcam)
        self.use_realsense = use_realsense and REALSENSE_AVAILABLE
        self.camera = None
        self.pipeline = None

        if self.use_realsense:
            self._init_realsense_camera()
        else:
            self._init_standard_camera()

        print("System initialized successfully!")
        print(f"Loaded {len(self.state_manager.steps)} task steps")
        print("\nControls:")
        print("  'q' - Quit")
        print("  'r' - Reset procedure")
        print("  'c' - Recalibrate AprilTag markers")
        print("  'd' - Toggle debug mode (show color masks)")
        print("  's' - Show full state status (verbose)")
        print("\nNOTE: If tape/blocks aren't detected, run calibrate_colors.py to tune colors")
        print("\n" + "="*50)

    def _init_realsense_camera(self):
        """Initialize RealSense D435i camera"""
        print("Initializing RealSense camera...")

        try:
            self.pipeline = rs.pipeline()
            config = rs.config()

            # Configure color stream only (we don't need depth for this application)
            config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

            # Start pipeline
            self.pipeline.start(config)

            print("  ✓ RealSense camera initialized")
            print("    → Color stream: 1280×720 @ 30fps")

        except Exception as e:
            print(f"  ✗ Failed to initialize RealSense: {e}")
            print("  → Falling back to standard webcam...")
            self.use_realsense = False
            self._init_standard_camera()

    def _init_standard_camera(self):
        """Initialize standard webcam"""
        print("Initializing standard webcam...")

        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            raise RuntimeError("Failed to open camera 0")

        # Set camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera.set(cv2.CAP_PROP_FPS, 30)

        print("  ✓ Standard webcam initialized")

    def run(self):
        """Main application loop."""
        try:
            while True:
                # Capture frame
                frame = self._get_frame()
                if frame is None:
                    print("Failed to capture frame")
                    break

                # Update perception modules
                self.surface_tracker.update(frame)
                self.object_detector.detect(frame, self.surface_tracker)
                hands_detected = self.hand_tracker.update(frame)

                # Debug: Print hand detection status occasionally
                # if frame_count := getattr(self, '_frame_count', 0) % 30 == 0:
                #     if hands_detected:
                #         print(f"✓ Hands detected: {len(self.hand_tracker.hand_centers)}")
                # self._frame_count = getattr(self, '_frame_count', 0) + 1

                # Update state
                self.state_manager.update(
                    self.surface_tracker,
                    self.object_detector,
                    self.hand_tracker
                )

                # Render visualization
                output = self.renderer.render_frame(
                    frame,
                    self.surface_tracker,
                    self.object_detector,
                    self.hand_tracker,
                    self.state_manager
                )

                # Show frame
                cv2.imshow('Table Organization Guidance System', output)

                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('r'):
                    print("\nResetting procedure...")
                    self.state_manager.reset()
                elif key == ord('c'):
                    print("\nRecalibrating AprilTag markers...")
                    self.surface_tracker.homography_matrix = None
                elif key == ord('d'):
                    # Toggle debug mode for color-based detection
                    if hasattr(self.object_detector, 'set_debug_mode'):
                        current_debug = getattr(self.object_detector.color_detector, 'debug_mode', False)
                        self.object_detector.set_debug_mode(not current_debug)
                        print(f"\nDebug mode: {'ON' if not current_debug else 'OFF'}")
                elif key == ord('s'):
                    # Show full state status
                    self._print_full_status()

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")

        finally:
            self.cleanup()

    def _print_full_status(self):
        """Print comprehensive state management status."""
        status = self.state_manager.get_full_status()

        print("\n" + "="*70)
        print("STATE MANAGEMENT STATUS")
        print("="*70)

        print("\nA. PROCEDURE PROGRESS:")
        print(f"   Current Step: {status['procedure_progress']['current_step_number']}/{status['procedure_progress']['total_steps']}")
        print(f"   Description: {status['procedure_progress']['current_step_description']}")
        print(f"   Progress Text: {status['procedure_progress']['progress_text']}")
        print(f"   State: {status['procedure_progress']['state']}")

        print("\nB. VISIBILITY:")
        print(f"   Table Surface Visible: {status['visibility']['table_surface_visible']}")
        print(f"   Target Object Detected: {status['visibility']['target_object_detected']}")
        print(f"   Target Object Name: {status['visibility']['target_object_name']}")

        print("\nC. INTERACTION STATUS (Inferred):")
        print(f"   Hand Near Object: {status['interaction_status']['hand_near_object']}")
        print(f"   Object Moving: {status['interaction_status']['object_moving']}")
        print(f"   User Is Moving Item: {status['interaction_status']['user_is_moving_item']} ⚡")

        print("\nD. COMPLETION STATUS:")
        print(f"   Current Step Complete: {status['completion_status']['current_step_complete']}")
        print(f"   Procedure Complete: {status['completion_status']['procedure_complete']}")
        print(f"   Completed Steps: {status['completion_status']['completed_steps']}/{status['completion_status']['completed_steps'] + status['completion_status']['remaining_steps']}")
        print(f"   Remaining Steps: {status['completion_status']['remaining_steps']}")

        print("="*70 + "\n")

    def _get_frame(self):
        """Get a frame from the active camera source"""
        if self.use_realsense and self.pipeline:
            try:
                frames = self.pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if not color_frame:
                    return None

                # Convert to numpy array
                frame = np.asanyarray(color_frame.get_data())
                return frame

            except Exception as e:
                print(f"Error getting RealSense frame: {e}")
                return None
        else:
            ret, frame = self.camera.read()
            return frame if ret else None

    def cleanup(self):
        """Release resources."""
        print("Cleaning up...")

        if self.use_realsense and self.pipeline:
            self.pipeline.stop()
            print("  ✓ RealSense pipeline stopped")
        elif self.camera:
            self.camera.release()
            print("  ✓ Camera released")

        self.hand_tracker.release()
        cv2.destroyAllWindows()
        print("Goodbye!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Table Organization Guidance System'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='../config/procedure_config.json',
        help='Path to procedure configuration file'
    )
    parser.add_argument(
        '--no-realsense',
        action='store_true',
        help='Disable RealSense and use standard webcam'
    )

    args = parser.parse_args()

    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Please create a procedure configuration file.")
        sys.exit(1)

    # Run the system
    try:
        use_realsense = not args.no_realsense
        system = TableGuidanceSystem(str(config_path), use_realsense=use_realsense)
        system.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Hybrid Color Calibration Utility
Helps calibrate color ranges for tape and block detection.
"""

import cv2
import numpy as np
import sys
sys.path.insert(0, '.')

try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False

from perception import ObjectDetector


class HybridColorCalibrator:
    def __init__(self, use_realsense=True):
        self.use_realsense = use_realsense and REALSENSE_AVAILABLE
        self.detector = ObjectDetector()
        self.detector.set_debug_mode(True)

        # Camera setup
        if self.use_realsense:
            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
            self.pipeline.start(config)
            self.camera = None
            print("Using RealSense camera")
        else:
            self.camera = cv2.VideoCapture(0)
            self.pipeline = None
            print("Using standard webcam")

        # Configure for tape and block only
        self.detector.object_configs = {
            'tape': {
                'color_ranges': [
                    # Default beige/tan for masking tape
                    (np.array([15, 20, 100]), np.array([35, 180, 255]))
                ],
                'min_area': 200,
                'max_area': 50000,
                'aspect_ratio_range': (0.3, 4.0)
            },
            'block': {
                'color_ranges': [
                    # Default - wide range, needs calibration
                    (np.array([0, 40, 40]), np.array([180, 255, 255]))
                ],
                'min_area': 100,
                'max_area': 30000,
                'aspect_ratio_range': (0.5, 2.0)
            }
        }

        # Current calibration state
        self.current_object = 'tape'
        self.objects = ['tape', 'block']
        self.click_points = []
        self.frame = None

        print("\n" + "="*70)
        print("HYBRID COLOR CALIBRATION UTILITY")
        print("="*70)
        print("\nInstructions:")
        print("  1. Press 1/2 to select object to calibrate:")
        print("     1 = Tape, 2 = Block")
        print("  2. Click on the object multiple times (5-10 points)")
        print("  3. Press SPACE to apply calibration")
        print("  4. Press 'c' to clear points")
        print("  5. Press 'd' to toggle debug masks")
        print("  6. Press 's' to save configuration")
        print("  7. Press 'q' to quit")
        print("\nTIPS:")
        print("  - Click on various parts of the object for best results")
        print("  - Avoid clicking on shadows or reflections")
        print("  - For tape: click on the tape surface, not the edge")
        print("  - For blocks: click on the flat colored surface")
        print("="*70 + "\n")

    def get_frame(self):
        """Get frame from camera."""
        if self.use_realsense and self.pipeline:
            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if color_frame:
                return np.asanyarray(color_frame.get_data())
        elif self.camera:
            ret, frame = self.camera.read()
            if ret:
                return frame
        return None

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to sample colors."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.click_points.append((x, y))
            print(f"  Point {len(self.click_points)}: ({x}, {y})")

            # Draw click point
            if self.frame is not None:
                cv2.circle(self.frame, (x, y), 5, (0, 255, 0), -1)

    def run(self):
        """Main calibration loop."""
        cv2.namedWindow('Calibration')
        cv2.setMouseCallback('Calibration', self.mouse_callback)

        while True:
            frame = self.get_frame()
            if frame is None:
                print("Failed to get frame")
                break

            self.frame = frame.copy()

            # Run detection with current settings
            self.detector.detect(frame)

            # Draw current object detections
            for obj_name in self.objects:
                obj_info = self.detector.get_object_info(obj_name)
                if obj_info and obj_info['detected']:
                    bbox = obj_info['bbox']
                    if bbox:
                        x, y, w, h = bbox
                        color = (0, 255, 0) if obj_name == self.current_object else (100, 100, 100)
                        cv2.rectangle(self.frame, (x, y), (x+w, y+h), color, 2)
                        cv2.putText(self.frame, obj_name.upper(), (x, y-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Draw click points
            for i, (px, py) in enumerate(self.click_points):
                cv2.circle(self.frame, (px, py), 5, (0, 255, 255), -1)
                cv2.putText(self.frame, str(i+1), (px+10, py),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # Draw UI
            status = f"Calibrating: {self.current_object.upper()} | Points: {len(self.click_points)}"
            cv2.rectangle(self.frame, (0, 0), (900, 40), (50, 50, 50), -1)
            cv2.putText(self.frame, status, (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Instructions overlay
            instructions = [
                "1/2: Select object | SPACE: Apply | C: Clear | D: Debug | S: Save | Q: Quit"
            ]
            y_offset = frame.shape[0] - 20
            for text in instructions:
                cv2.putText(self.frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow('Calibration', self.frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('1'):
                self.current_object = 'tape'
                self.click_points = []
                print(f"\nSelected: TAPE")
            elif key == ord('2'):
                self.current_object = 'block'
                self.click_points = []
                print(f"\nSelected: BLOCK")
            elif key == ord('c'):
                self.click_points = []
                print("Cleared click points")
            elif key == ord('d'):
                self.detector.debug_mode = not self.detector.debug_mode
                print(f"Debug mode: {'ON' if self.detector.debug_mode else 'OFF'}")
            elif key == ord(' '):
                if len(self.click_points) >= 3:
                    print(f"\nCalibrating {self.current_object}...")
                    self.detector.calibrate_color(frame, self.current_object, self.click_points)
                    self.click_points = []
                    print("Calibration applied!")
                else:
                    print("Need at least 3 click points!")
            elif key == ord('s'):
                print("\n" + "="*70)
                print("COPY THESE VALUES TO main.py (color_objects section):")
                print("="*70)
                for obj_name, config in self.detector.object_configs.items():
                    print(f"\n'{obj_name}': {{")
                    print(f"    'color_ranges': [")
                    for i, (lower, upper) in enumerate(config['color_ranges']):
                        print(f"        (np.array({lower.tolist()}), np.array({upper.tolist()}))")
                        if i < len(config['color_ranges']) - 1:
                            print(",")
                    print(f"    ],")
                    print(f"    'min_area': {config['min_area']},")
                    print(f"    'max_area': {config['max_area']},")
                    print(f"    'aspect_ratio_range': {config['aspect_ratio_range']}")
                    print(f"}},")
                print("\n" + "="*70)

        # Cleanup
        if self.use_realsense and self.pipeline:
            self.pipeline.stop()
        elif self.camera:
            self.camera.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    calibrator = HybridColorCalibrator(use_realsense=True)
    calibrator.run()

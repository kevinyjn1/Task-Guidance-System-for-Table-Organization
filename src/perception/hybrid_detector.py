"""
Hybrid Object Detector
Combines YOLO for common objects with color-based detection for custom objects.
"""

import cv2
import numpy as np


class HybridObjectDetector:
    """
    Hybrid detector that uses YOLO for some objects and color-based detection for others.
    """

    def __init__(self, yolo_objects=None, color_objects=None):
        """
        Initialize hybrid detector.

        Args:
            yolo_objects: List of objects to detect with YOLO (e.g., ['bottle'])
            color_objects: Dict of objects with color-based detection config
                          e.g., {'tape': {...}, 'block': {...}}
        """
        self.yolo_objects = yolo_objects or ['bottle']
        self.color_objects = color_objects or {}
        self.detected_objects = {}

        # Initialize YOLO detector
        self.yolo_detector = None
        try:
            from .object_detector import COCOObjectDetector
            # Map YOLO objects
            yolo_mapping = {obj: obj for obj in self.yolo_objects}
            self.yolo_detector = COCOObjectDetector(backend='yolo', object_mapping=yolo_mapping)
            print(f"✓ YOLO detector loaded for: {self.yolo_objects}")
        except Exception as e:
            print(f"✗ Failed to load YOLO: {e}")

        # Initialize color-based detector
        from .object_detector import ObjectDetector
        self.color_detector = ObjectDetector()

        # Configure color ranges for custom objects
        if self.color_objects:
            self.color_detector.object_configs = self.color_objects
            print(f"✓ Color detector configured for: {list(self.color_objects.keys())}")

    def detect(self, frame, surface_tracker=None):
        """
        Detect objects using hybrid approach.

        Args:
            frame: Current camera frame
            surface_tracker: Optional surface tracker

        Returns:
            dict: Combined detection results
        """
        if frame is None:
            return {}

        combined_results = {}

        # YOLO detection for common objects
        if self.yolo_detector:
            yolo_results = self.yolo_detector.detect(frame, surface_tracker)
            for obj_name in self.yolo_objects:
                if obj_name in yolo_results:
                    combined_results[obj_name] = yolo_results[obj_name]

        # Color-based detection for custom objects
        if self.color_objects:
            color_results = self.color_detector.detect(frame, surface_tracker)
            for obj_name in self.color_objects.keys():
                if obj_name in color_results:
                    combined_results[obj_name] = color_results[obj_name]

        self.detected_objects = combined_results
        return combined_results

    def get_object_info(self, object_name):
        """Get detection info for a specific object."""
        return self.detected_objects.get(object_name)

    def is_object_detected(self, object_name):
        """Check if object is detected."""
        obj_info = self.detected_objects.get(object_name)
        return obj_info is not None and obj_info.get('detected', False)

    def calibrate_color(self, frame, object_name, click_points):
        """
        Calibrate color range for a custom object.

        Args:
            frame: Current frame
            object_name: Object to calibrate
            click_points: List of (x, y) click points

        Returns:
            tuple: (lower_hsv, upper_hsv)
        """
        if object_name in self.color_objects:
            return self.color_detector.calibrate_color(frame, object_name, click_points)
        return None

    def set_debug_mode(self, enabled):
        """Enable/disable debug visualization."""
        self.color_detector.set_debug_mode(enabled)

    def print_config(self):
        """Print current configuration."""
        print("\n" + "="*60)
        print("Hybrid Detector Configuration")
        print("="*60)
        print(f"\nYOLO Objects: {self.yolo_objects}")
        print(f"Color-based Objects: {list(self.color_objects.keys())}")
        if self.color_objects:
            print("\nColor Detection Settings:")
            self.color_detector.print_config()
        print("="*60 + "\n")

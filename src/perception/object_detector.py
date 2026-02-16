"""
Object Detector Module
Detects and tracks common objects using improved color-based segmentation with calibration support.
Can be extended to use YOLO or other deep learning models.
"""

import cv2
import numpy as np


class ObjectDetector:
    """
    Detects objects using color-based segmentation with improved robustness.
    Supports easy calibration for custom colored objects.
    """

    def __init__(self):
        """
        Initialize the object detector with color ranges for different objects.
        """

        # HSV color ranges for object detection (more permissive ranges)
        # For RED objects (cup) - need two ranges since red wraps around in HSV
        self.object_configs = {
            'cup': {
                'color_ranges': [
                    # Lower red range (0-10)
                    (np.array([0, 50, 50]), np.array([10, 255, 255])),
                    # Upper red range (170-180)
                    (np.array([170, 50, 50]), np.array([180, 255, 255]))
                ],
                'min_area': 300,
                'max_area': 100000,
                'aspect_ratio_range': (0.3, 3.0)  # h/w ratio
            },
            'bottle': {
                'color_ranges': [
                    # Blue range - more permissive
                    (np.array([90, 40, 40]), np.array([130, 255, 255]))
                ],
                'min_area': 500,
                'max_area': 150000,
                'aspect_ratio_range': (0.5, 5.0)  # Bottles are tall
            },
            'plate': {
                'color_ranges': [
                    # White/light colors - very broad range
                    (np.array([0, 0, 150]), np.array([180, 60, 255]))
                ],
                'min_area': 1000,
                'max_area': 200000,
                'aspect_ratio_range': (0.5, 2.0)  # Plates are roundish
            }
        }

        # Store detected objects
        self.detected_objects = {}

        # Debug mode shows HSV masks
        self.debug_mode = False

    def detect(self, frame, surface_tracker=None):
        """
        Detect objects in the current frame.

        Args:
            frame: Current camera frame (BGR image)
            surface_tracker: Optional SurfaceTracker to filter detections to table area

        Returns:
            dict: Dictionary mapping object names to detection info
        """
        if frame is None:
            return {}

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Apply slight blur to reduce noise
        hsv = cv2.GaussianBlur(hsv, (5, 5), 0)

        self.detected_objects = {}

        for obj_name, config in self.object_configs.items():
            # Combine multiple color ranges if present (e.g., for red)
            combined_mask = None

            for color_lower, color_upper in config['color_ranges']:
                # Create mask for this color range
                mask = cv2.inRange(hsv, color_lower, color_upper)

                if combined_mask is None:
                    combined_mask = mask
                else:
                    # Combine masks with OR operation
                    combined_mask = cv2.bitwise_or(combined_mask, mask)

            mask = combined_mask

            # Apply morphological operations to reduce noise
            kernel_open = np.ones((3, 3), np.uint8)
            kernel_close = np.ones((7, 7), np.uint8)

            # Remove small noise
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=2)
            # Fill holes
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)

            # Optional: Show debug masks
            if self.debug_mode:
                cv2.imshow(f'Mask: {obj_name}', mask)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            detected = False
            bbox = None
            center = None
            best_contour = None
            max_score = 0

            if contours:
                # Score contours based on area and aspect ratio
                for contour in contours:
                    area = cv2.contourArea(contour)

                    # Check area constraints
                    if not (config['min_area'] < area < config['max_area']):
                        continue

                    # Get bounding box
                    x, y, w, h = cv2.boundingRect(contour)

                    # Check aspect ratio (height/width)
                    aspect_ratio = h / w if w > 0 else 0
                    min_ar, max_ar = config['aspect_ratio_range']

                    if not (min_ar < aspect_ratio < max_ar):
                        continue

                    # Calculate center
                    cx = x + w // 2
                    cy = y + h // 2

                    # Check if center is on table (if tracker available)
                    if surface_tracker and not surface_tracker.is_point_in_table((cx, cy)):
                        continue

                    # Score based on area (prefer larger objects)
                    score = area

                    if score > max_score:
                        max_score = score
                        best_contour = contour
                        bbox = (x, y, w, h)
                        center = (cx, cy)
                        detected = True

            self.detected_objects[obj_name] = {
                'detected': detected,
                'bbox': bbox,
                'center': center,
                'contour': best_contour,
                'area': max_score if detected else 0
            }

        return self.detected_objects

    def get_object_info(self, object_name):
        """
        Get detection info for a specific object.

        Args:
            object_name: Name of the object ('cup', 'bottle', or 'plate')

        Returns:
            dict: Detection info or None if object not found
        """
        return self.detected_objects.get(object_name)

    def is_object_detected(self, object_name):
        """
        Check if a specific object is currently detected.

        Args:
            object_name: Name of the object

        Returns:
            bool: True if object is detected
        """
        obj_info = self.detected_objects.get(object_name)
        return obj_info is not None and obj_info['detected']

    def calibrate_color(self, frame, object_name, click_points):
        """
        Calibrate color range for an object by sampling clicked points.

        Args:
            frame: Current BGR frame
            object_name: Name of object to calibrate
            click_points: List of (x, y) points clicked by user

        Returns:
            tuple: (lower_hsv, upper_hsv) color range
        """
        if not click_points or object_name not in self.object_configs:
            return None

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Sample HSV values at clicked points
        sampled_hsvs = []
        for x, y in click_points:
            if 0 <= y < hsv.shape[0] and 0 <= x < hsv.shape[1]:
                sampled_hsvs.append(hsv[y, x])

        if not sampled_hsvs:
            return None

        sampled_hsvs = np.array(sampled_hsvs)

        # Calculate mean and std
        mean_hsv = np.mean(sampled_hsvs, axis=0)
        std_hsv = np.std(sampled_hsvs, axis=0)

        # Create range with 2-sigma margin
        margin = 2.5
        lower = np.maximum(mean_hsv - margin * std_hsv, [0, 30, 30])
        upper = np.minimum(mean_hsv + margin * std_hsv, [180, 255, 255])

        lower = lower.astype(np.uint8)
        upper = upper.astype(np.uint8)

        print(f"\nCalibrated {object_name}:")
        print(f"  Lower HSV: {lower}")
        print(f"  Upper HSV: {upper}")

        # Update config
        self.object_configs[object_name]['color_ranges'] = [(lower, upper)]

        return (lower, upper)

    def set_debug_mode(self, enabled):
        """Enable/disable debug visualization of color masks."""
        self.debug_mode = enabled
        if not enabled:
            cv2.destroyAllWindows()

    def print_config(self):
        """Print current color configuration for all objects."""
        print("\n" + "="*60)
        print("Current Object Detection Configuration")
        print("="*60)
        for obj_name, config in self.object_configs.items():
            print(f"\n{obj_name.upper()}:")
            for i, (lower, upper) in enumerate(config['color_ranges']):
                print(f"  Range {i+1}:")
                print(f"    Lower HSV: {lower}")
                print(f"    Upper HSV: {upper}")
            print(f"  Area range: {config['min_area']} - {config['max_area']}")
            print(f"  Aspect ratio: {config['aspect_ratio_range']}")
        print("="*60 + "\n")


# Alternative: Model-based detector using COCO pre-trained models
class COCOObjectDetector:
    """
    Object detector using pre-trained COCO models (YOLO, Mask R-CNN, etc.)
    More robust but requires model files and more compute.
    """

    def __init__(self, backend='yolo', model_path=None, object_mapping=None):
        """
        Initialize model-based detector.

        Args:
            backend: 'yolo' or 'maskrcnn'
            model_path: Path to model file
            object_mapping: Custom mapping of COCO classes to object names
                          e.g., {'bottle': 'bottle', 'cup': 'cup', 'book': 'block'}
        """
        self.backend = backend
        self.detected_objects = {}

        # Default mapping (can be overridden)
        if object_mapping is None:
            # Map COCO class names to our object names
            self.class_mapping = {
                'cup': 'cup',
                'bottle': 'bottle',
                'bowl': 'plate',  # Use bowl as plate
            }
        else:
            self.class_mapping = object_mapping

        if backend == 'yolo':
            try:
                from ultralytics import YOLO
                model_path = model_path or 'yolov8n.pt'
                self.model = YOLO(model_path)
                self.enabled = True
                print(f"✓ YOLO detector loaded: {model_path}")
            except Exception as e:
                print(f"✗ Failed to load YOLO: {e}")
                self.enabled = False
        else:
            print(f"Backend '{backend}' not implemented")
            self.enabled = False

    def detect(self, frame, surface_tracker=None):
        """Detect objects using the model."""
        if not self.enabled:
            return {}

        results = self.model(frame, verbose=False, conf=0.5)
        detected_objects = {}

        # Track best detection for each object type
        best_detections = {}

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                confidence = float(box.conf[0])

                # Map to our object names
                if class_name in self.class_mapping:
                    our_name = self.class_mapping[class_name]

                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    center = (cx, cy)
                    bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))

                    # Check if on table
                    if surface_tracker and not surface_tracker.is_point_in_table(center):
                        continue

                    # Keep best detection (highest confidence)
                    if our_name not in best_detections or confidence > best_detections[our_name]['confidence']:
                        best_detections[our_name] = {
                            'detected': True,
                            'bbox': bbox,
                            'center': center,
                            'confidence': confidence,
                            'class_name': class_name
                        }

        # Format output - use all object names from our mapping
        for obj_name in set(self.class_mapping.values()):
            if obj_name in best_detections:
                detected_objects[obj_name] = best_detections[obj_name]
            else:
                detected_objects[obj_name] = {
                    'detected': False,
                    'bbox': None,
                    'center': None
                }

        self.detected_objects = detected_objects
        return detected_objects

    def get_object_info(self, object_name):
        """Get detection info for a specific object."""
        return self.detected_objects.get(object_name)

    def is_object_detected(self, object_name):
        """Check if object is detected."""
        obj_info = self.detected_objects.get(object_name)
        return obj_info is not None and obj_info.get('detected', False)

"""
Surface Tracker Module
Uses AprilTag markers to define and track the table surface coordinate system.
"""

import cv2
import numpy as np

try:
    from pupil_apriltags import Detector
    APRILTAG_AVAILABLE = True
except ImportError:
    APRILTAG_AVAILABLE = False
    print("Warning: pupil-apriltags not available. Please install: pip install pupil-apriltags")


class SurfaceTracker:
    """
    Tracks the table surface using AprilTag markers (tag36h11 family) placed at the corners.
    Computes homography matrix to map between camera coordinates and table coordinates.
    """

    def __init__(self, marker_size=0.05, marker_ids=[0, 1, 2, 3]):
        """
        Initialize the surface tracker.

        Args:
            marker_size: Physical size of AprilTag markers in meters
            marker_ids: List of marker IDs to use for table corners (expected in order: TL, TR, BR, BL)
        """
        self.marker_size = marker_size
        self.marker_ids = marker_ids
        self.enabled = APRILTAG_AVAILABLE

        # AprilTag detector setup
        if self.enabled:
            self.detector = Detector(
                families='tag36h11',
                nthreads=1,
                quad_decimate=1.0,
                quad_sigma=0.0,
                refine_edges=1,
                decode_sharpening=0.25,
                debug=0
            )
        else:
            self.detector = None

        # Table coordinate system (in pixels, will be set during calibration)
        self.table_width = 800
        self.table_height = 600

        # Homography matrix (camera coords -> table coords)
        self.homography_matrix = None
        self.inverse_homography = None

        # Detected corners in camera coordinates
        self.detected_corners = None
        self.is_visible = False

    def update(self, frame):
        """
        Update surface tracking with a new frame.

        Args:
            frame: Current camera frame (BGR image)

        Returns:
            bool: True if surface is successfully detected and tracked
        """
        if not self.enabled:
            return False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect AprilTags
        tags = self.detector.detect(
            gray,
            estimate_tag_pose=False,
            camera_params=None,
            tag_size=self.marker_size
        )

        if len(tags) < 4:
            self.is_visible = False
            self.detected_corners = None
            return False

        # Find our specific markers
        marker_corners = {}
        for tag in tags:
            if tag.tag_id in self.marker_ids:
                # Get center of marker
                center = tag.center
                marker_corners[tag.tag_id] = center

        # Check if we have all 4 markers
        if len(marker_corners) < 4:
            self.is_visible = False
            self.detected_corners = None
            return False

        # Order corners: TL(0), TR(1), BR(2), BL(3)
        src_points = np.float32([
            marker_corners[self.marker_ids[0]],  # Top-left
            marker_corners[self.marker_ids[1]],  # Top-right
            marker_corners[self.marker_ids[2]],  # Bottom-right
            marker_corners[self.marker_ids[3]]   # Bottom-left
        ])

        # Define destination points in table coordinate system
        dst_points = np.float32([
            [0, 0],
            [self.table_width, 0],
            [self.table_width, self.table_height],
            [0, self.table_height]
        ])

        # Compute homography
        self.homography_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        self.inverse_homography = cv2.getPerspectiveTransform(dst_points, src_points)

        self.detected_corners = src_points
        self.is_visible = True

        return True

    def camera_to_table(self, point):
        """
        Convert a point from camera coordinates to table coordinates.

        Args:
            point: (x, y) tuple in camera coordinates

        Returns:
            (x, y) tuple in table coordinates, or None if surface not tracked
        """
        if self.homography_matrix is None:
            return None

        point_array = np.array([[point]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point_array, self.homography_matrix)
        return tuple(transformed[0][0])

    def table_to_camera(self, point):
        """
        Convert a point from table coordinates to camera coordinates.

        Args:
            point: (x, y) tuple in table coordinates

        Returns:
            (x, y) tuple in camera coordinates, or None if surface not tracked
        """
        if self.inverse_homography is None:
            return None

        point_array = np.array([[point]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point_array, self.inverse_homography)
        return tuple(transformed[0][0])

    def is_point_in_table(self, point):
        """
        Check if a point in camera coordinates is within the table bounds.

        Args:
            point: (x, y) tuple in camera coordinates

        Returns:
            bool: True if point is within table bounds
        """
        table_point = self.camera_to_table(point)
        if table_point is None:
            return False

        x, y = table_point
        return 0 <= x <= self.table_width and 0 <= y <= self.table_height

    def get_table_boundary_points(self):
        """
        Get the four corner points of the table in camera coordinates.

        Returns:
            numpy array of shape (4, 2) or None if surface not tracked
        """
        return self.detected_corners

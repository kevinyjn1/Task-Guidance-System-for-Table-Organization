"""
Helper utility functions.
"""

import cv2
import numpy as np
from pathlib import Path


def distance(point1, point2):
    """
    Calculate Euclidean distance between two points.

    Args:
        point1: (x, y) tuple
        point2: (x, y) tuple

    Returns:
        float: Distance between points
    """
    if point1 is None or point2 is None:
        return float('inf')

    x1, y1 = point1
    x2, y2 = point2
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def is_point_in_bbox(point, bbox):
    """
    Check if a point is inside a bounding box.

    Args:
        point: (x, y) tuple
        bbox: (x, y, w, h) tuple

    Returns:
        bool: True if point is inside bbox
    """
    if point is None or bbox is None:
        return False

    px, py = point
    x, y, w, h = bbox

    return x <= px <= x + w and y <= py <= y + h


def generate_aruco_markers(output_dir='assets', marker_size=200, marker_ids=[0, 1, 2, 3]):
    """
    Generate ArUco marker images for printing.

    Args:
        output_dir: Directory to save marker images
        marker_size: Size of markers in pixels
        marker_ids: List of marker IDs to generate
    """
    from cv2 import aruco

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

    for marker_id in marker_ids:
        marker_image = aruco.generateImageMarker(aruco_dict, marker_id, marker_size)

        filename = output_path / f"aruco_marker_{marker_id}.png"
        cv2.imwrite(str(filename), marker_image)
        print(f"Generated marker {marker_id}: {filename}")


def generate_apriltag_info(marker_ids=[0, 1, 2, 3]):
    """
    Generate information for AprilTag markers.

    Args:
        marker_ids: List of marker IDs to use

    Returns:
        str: Information about where to download AprilTag markers
    """
    info = """
    AprilTag Marker Setup
    =====================

    This system uses AprilTag markers from the 'tag36h11' family.

    Markers needed: {}

    To generate these markers:

    1. Visit: https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11
    2. Download the following images:
       {}

    3. Print them on white paper (recommended size: 5-10cm each)
    4. Place them at the four corners of your table:
       - Marker 0: Top-left corner
       - Marker 1: Top-right corner
       - Marker 2: Bottom-right corner
       - Marker 3: Bottom-left corner

    Tips:
    - Ensure markers are flat and visible to the camera
    - Avoid shadows and glare on the markers
    - Keep some white border around each marker when cutting
    """.format(
        marker_ids,
        '\n       '.join([f"tag36_11_{mid:05d}.png" for mid in marker_ids])
    )

    return info


if __name__ == '__main__':
    # Generate marker information
    print(generate_apriltag_info())

    # Note: To generate ArUco markers, uncomment:
    # generate_aruco_markers()

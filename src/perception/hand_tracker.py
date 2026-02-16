"""
Hand Tracker Module
Uses MediaPipe to detect and track hands in the workspace.
"""

import cv2
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("Warning: MediaPipe not available. Hand tracking will be disabled.")


class HandTracker:
    """
    Tracks hands using MediaPipe Hands solution.
    Provides information about hand presence and position.
    """

    def __init__(self, max_hands=2, detection_confidence=0.3, tracking_confidence=0.3):
        """
        Initialize the hand tracker.

        Args:
            max_hands: Maximum number of hands to detect
            detection_confidence: Minimum confidence for hand detection (lowered to 0.3 for better detection)
            tracking_confidence: Minimum confidence for hand tracking (lowered to 0.3 for better detection)
        """
        self.enabled = MEDIAPIPE_AVAILABLE
        self.hands = None
        self.mp_hands = None
        self.mp_draw = None

        if self.enabled:
            try:
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=max_hands,
                    min_detection_confidence=detection_confidence,  # Lowered from 0.5 to 0.3
                    min_tracking_confidence=tracking_confidence      # Lowered from 0.5 to 0.3
                )
                self.mp_draw = mp.solutions.drawing_utils
            except (AttributeError, Exception) as e:
                print(f"Warning: MediaPipe initialization failed: {e}")
                print("Hand tracking will be disabled.")
                self.enabled = False
                self.hands = None
                self.mp_hands = None
                self.mp_draw = None

        # Tracked hand information
        self.hand_landmarks = []
        self.hand_centers = []
        self.hands_detected = False

    def update(self, frame):
        """
        Update hand tracking with a new frame.

        Args:
            frame: Current camera frame (BGR image)

        Returns:
            bool: True if at least one hand is detected
        """
        if not self.enabled:
            return False

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame
        results = self.hands.process(rgb_frame)

        # Reset tracking data
        self.hand_landmarks = []
        self.hand_centers = []
        self.hands_detected = False

        # Extract hand landmarks
        if results.multi_hand_landmarks:
            self.hands_detected = True
            h, w, _ = frame.shape

            for hand_landmarks in results.multi_hand_landmarks:
                self.hand_landmarks.append(hand_landmarks)

                # Calculate hand center (using wrist and middle finger MCP)
                wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
                middle_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]

                center_x = int((wrist.x + middle_mcp.x) / 2 * w)
                center_y = int((wrist.y + middle_mcp.y) / 2 * h)
                self.hand_centers.append((center_x, center_y))

        return self.hands_detected

    def is_hand_near_object(self, object_center, threshold=100):
        """
        Check if any hand is near a specific object.

        Args:
            object_center: (x, y) tuple representing object center
            threshold: Distance threshold in pixels

        Returns:
            bool: True if any hand is within threshold distance of the object
        """
        if not self.hands_detected or object_center is None:
            return False

        obj_x, obj_y = object_center

        for hand_x, hand_y in self.hand_centers:
            distance = np.sqrt((hand_x - obj_x) ** 2 + (hand_y - obj_y) ** 2)
            if distance < threshold:
                return True

        return False

    def get_hand_centers(self):
        """
        Get centers of all detected hands.

        Returns:
            list: List of (x, y) tuples representing hand centers
        """
        return self.hand_centers

    def draw_hands(self, frame):
        """
        Draw hand landmarks on the frame.

        Args:
            frame: Frame to draw on (BGR image)

        Returns:
            frame: Frame with hand landmarks drawn
        """
        if not self.enabled or not self.hands_detected:
            return frame

        for hand_landmarks in self.hand_landmarks:
            self.mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=4),  # Thicker/larger
                self.mp_draw.DrawingSpec(color=(255, 0, 0), thickness=3)
            )

        # Draw hand centers - make them VERY visible
        for center in self.hand_centers:
            cv2.circle(frame, center, 15, (0, 255, 255), -1)  # Larger yellow circle
            cv2.circle(frame, center, 18, (0, 0, 0), 3)  # Thicker black border

        # Add text indicator
        if len(self.hand_centers) > 0:
            cv2.putText(
                frame,
                f"HANDS: {len(self.hand_centers)}",
                (frame.shape[1] - 200, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        return frame

    def release(self):
        """Release MediaPipe resources."""
        if self.enabled and self.hands:
            self.hands.close()

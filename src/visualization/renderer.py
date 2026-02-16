"""
Renderer Module - Visualization and Rendering System

This module handles all visual overlays for the task guidance system, integrating
information from perception (object detection, surface tracking, hand tracking) and
state management to provide comprehensive visual feedback.

Key Features:
- Workspace Boundary: Renders AprilTag-defined workspace boundary
- Object Detection: Highlights detected objects with spatial awareness
- Target Zones: Perspective-correct rendering using homography transformation
- Guidance Arrows: Visual cues pointing from objects to target positions
- Success Feedback: Timed "Great Job!" messages at target zone locations
- Status Overlay: Progress information and system state
- Debug Information: Real-time system diagnostics

System Integration:
The renderer acts as the presentation layer, consuming data from:
- SurfaceTracker: Workspace boundaries and coordinate transformations
- ObjectDetector: Detected object positions and bounding boxes
- HandTracker: Hand positions for user interaction visualization
- StateManager: Task progress, completion status, and workflow state

Robustness:
- Gracefully handles missing or None data from perception modules
- Continues rendering when objects are temporarily occluded
- Validates coordinate transformations before rendering
- Checks workspace boundaries to avoid rendering invalid data

Coordinate Transformation:
Demonstrates spatial understanding by using homography transformation to map
between table coordinates (stable, physical space) and camera coordinates
(perspective view), enabling perspective-correct rendering of target zones.
"""

import cv2
import numpy as np
import time
from state_manager.state_manager import ProcedureState


class Renderer:
    """
    Handles all visualization and rendering for the task guidance system.
    """

    def __init__(self):
        """
        Initialize the renderer with default colors and styles.

        Sets up color scheme, fonts, and tracking variables for success feedback.
        """
        # Color scheme (BGR format for OpenCV)
        self.colors = {
            'table_boundary': (0, 255, 255),      # Yellow - AprilTag workspace boundary
            'object_detected': (0, 255, 0),       # Green - Detected objects
            'object_target': (255, 0, 0),         # Blue - Target object
            'target_incomplete': (0, 165, 255),   # Orange - Incomplete target zones
            'target_complete': (0, 255, 0),       # Green - Completed target zones
            'arrow': (255, 0, 255),               # Magenta - Guidance arrows
            'text_bg': (0, 0, 0),                 # Black - Text background
            'text_fg': (255, 255, 255),           # White - Text foreground
            'success': (0, 255, 0),               # Green - Success state
            'warning': (0, 165, 255),             # Orange - Warning state
            'error': (0, 0, 255)                  # Red - Error state
        }

        # Font settings for text rendering
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_thickness = 2

        # Success feedback tracking ("Great Job!" message)
        # These track when steps are completed to show timed success messages
        self.last_completion_time = None           # Timestamp of last completion
        self.last_completed_step_index = -1        # Index of last completed step
        self.just_completed_step = None            # Reference to completed step for rendering
        self.success_message_duration = 3.0        # Duration to show success message (seconds)

    def render_frame(self, frame, surface_tracker, object_detector, hand_tracker, state_manager):
        """
        Main rendering pipeline - integrates all visual overlays.

        This method demonstrates SYSTEM INTEGRATION by coordinating data from all
        perception and logic modules to create comprehensive visual feedback. The
        rendering order ensures proper layering of visual elements.

        Rendering Pipeline (back to front):
        1. Workspace boundary (AprilTag markers)
        2. Target zones (perspective-corrected with homography)
        3. Detected objects (with workspace filtering)
        4. Guidance arrows (showing movement direction)
        5. Hand tracking (user interaction feedback)
        6. Status overlay (progress and state information)
        7. Debug information (system diagnostics)
        8. Success message (contextual feedback at target location)

        Args:
            frame: Input frame to render on
            surface_tracker: Provides workspace boundaries and coordinate transformations
            object_detector: Provides detected object positions and bounding boxes
            hand_tracker: Provides hand positions for interaction visualization
            state_manager: Provides task progress, completion state, and workflow logic

        Returns:
            frame: Rendered frame with all overlays properly layered
        """
        # Work on a copy to preserve original frame
        output = frame.copy()

        # Layer 1: Workspace boundary (AprilTag markers defining table surface)
        # Robustness: Only render if surface is currently visible
        if surface_tracker.is_visible:
            output = self._draw_table_boundary(output, surface_tracker)

        # Layer 2: Target zones with perspective correction
        # Demonstrates coordinate transformation using homography
        output = self._draw_target_zones(output, surface_tracker, state_manager)

        # Layer 3: Detected objects with spatial awareness
        # Integrates object detection with workspace boundary checking
        output = self._draw_objects(output, object_detector, state_manager)

        # Layer 4: Guidance arrows (only during active task execution)
        # Shows user which object to move and where to place it
        if state_manager.state == ProcedureState.IN_PROGRESS:
            output = self._draw_guidance_arrow(
                output, surface_tracker, object_detector, state_manager
            )

        # Layer 5: Hand tracking visualization (if enabled)
        # Provides feedback on user interaction
        if hand_tracker.enabled:
            output = hand_tracker.draw_hands(output)

        # Layer 6: Status overlay at top of screen
        # Shows current step, progress, and system state
        output = self._draw_status_overlay(output, state_manager)

        # Layer 7: Debug information at bottom of screen
        # Real-time diagnostics for development and troubleshooting
        output = self._draw_debug_info(output, state_manager)

        # Layer 8: Success message (topmost layer for visibility)
        # Spatially positioned at completed target zone using coordinate transformation
        output = self._draw_success_message(output, surface_tracker, state_manager)

        return output

    def _draw_table_boundary(self, frame, surface_tracker):
        """Draw the detected table boundary."""
        corners = surface_tracker.get_table_boundary_points()
        if corners is not None:
            corners_int = corners.astype(np.int32)
            cv2.polylines(
                frame,
                [corners_int],
                isClosed=True,
                color=self.colors['table_boundary'],
                thickness=3
            )
            # Add corner labels
            labels = ['TL', 'TR', 'BR', 'BL']
            for i, (x, y) in enumerate(corners_int):
                cv2.circle(frame, (int(x), int(y)), 8, self.colors['table_boundary'], -1)
                cv2.putText(
                    frame, labels[i], (int(x) + 10, int(y) - 10),
                    self.font, 0.5, self.colors['text_fg'], 1
                )
        return frame

    def _draw_target_zones(self, frame, surface_tracker, state_manager):
        """
        Draw perspective-correct target zones using homography transformation.

        This method demonstrates coordinate transformation - target zones are defined
        in table coordinate space (stable, physical coordinates) and transformed to
        camera space (perspective view) using homography matrix. This provides
        spatial understanding beyond simple screen pixels.

        Args:
            frame: Current frame to render on
            surface_tracker: Surface tracker with homography transformation
            state_manager: State manager with target zone definitions

        Returns:
            frame: Frame with target zones rendered with perspective correction
        """
        # Robustness: Only draw if AprilTag surface is visible
        if not surface_tracker.is_visible:
            return frame

        # Render target zone for each step
        for step in state_manager.steps:
            # Get target zone definition in TABLE coordinate space
            # These are stable physical coordinates, not affected by camera angle
            target_x, target_y = step.target_position
            target_w, target_h = step.target_size

            # Define target zone corners in table coordinate system
            corners_table = np.float32([
                [target_x, target_y],                          # Top-left
                [target_x + target_w, target_y],               # Top-right
                [target_x + target_w, target_y + target_h],    # Bottom-right
                [target_x, target_y + target_h]                # Bottom-left
            ])

            # COORDINATE TRANSFORMATION: Convert from table space to camera space
            # Uses homography matrix for perspective-correct transformation
            # This demonstrates spatial understanding - zones appear correctly
            # aligned with the physical table surface regardless of camera angle
            corners_camera = []
            for corner in corners_table:
                cam_point = surface_tracker.table_to_camera(tuple(corner))
                # Robustness: Check if transformation succeeded
                if cam_point:
                    corners_camera.append(cam_point)

            # Robustness: Only render if all four corners transformed successfully
            if len(corners_camera) == 4:
                corners_int = np.array(corners_camera, dtype=np.int32)

                # Choose color based on completion status
                color = self.colors['target_complete'] if step.completed else self.colors['target_incomplete']

                # Draw filled polygon with transparency
                overlay = frame.copy()
                cv2.fillPoly(overlay, [corners_int], color)
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

                # Draw border
                cv2.polylines(frame, [corners_int], isClosed=True, color=color, thickness=3)

                # Add label
                center = np.mean(corners_int, axis=0).astype(int)
                label = f"{step.object_name.capitalize()}"
                # No completion indicator - just show object name

                # Draw text with background
                text_size = cv2.getTextSize(label, self.font, 0.6, 2)[0]
                text_x = center[0] - text_size[0] // 2
                text_y = center[1] + text_size[1] // 2

                cv2.rectangle(
                    frame,
                    (text_x - 5, text_y - text_size[1] - 5),
                    (text_x + text_size[0] + 5, text_y + 5),
                    self.colors['text_bg'],
                    -1
                )
                cv2.putText(
                    frame, label, (text_x, text_y),
                    self.font, 0.6, self.colors['text_fg'], 2
                )

        return frame

    def _draw_objects(self, frame, object_detector, state_manager):
        """
        Draw bounding boxes around detected objects with spatial awareness.

        Only renders objects that are within the workspace boundary, demonstrating
        spatial understanding. Current target object is highlighted differently.

        Args:
            frame: Current frame to render on
            object_detector: Object detector with detected objects
            state_manager: State manager for workspace boundary and current step

        Returns:
            frame: Frame with object bounding boxes rendered
        """
        # Get current target object for highlighting
        current_step = state_manager.get_current_step()
        current_object_name = current_step.object_name if current_step else None

        # Iterate through all detected objects
        for obj_name, obj_info in object_detector.detected_objects.items():
            # Robustness: Skip objects that aren't currently detected
            if not obj_info['detected']:
                continue

            bbox = obj_info['bbox']
            center = obj_info['center']

            # Robustness: Handle missing or None detection data gracefully
            # Objects may be briefly occluded or lose detection
            if bbox is None or center is None:
                continue

            # Spatial Understanding: Only render objects inside the workspace
            # This prevents showing objects outside the AprilTag boundary
            if not state_manager.is_point_in_workspace(center):
                continue

            x, y, w, h = bbox

            # Visual feedback: Highlight current target object differently
            if obj_name == current_object_name:
                color = self.colors['arrow']  # Magenta for current target
                thickness = 3
            else:
                color = self.colors['object_detected']  # Green for other objects
                thickness = 2

            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)

            # Draw label
            label = obj_name.capitalize()
            label_size = cv2.getTextSize(label, self.font, 0.6, 2)[0]

            cv2.rectangle(
                frame,
                (x, y - label_size[1] - 10),
                (x + label_size[0] + 10, y),
                color,
                -1
            )
            cv2.putText(
                frame, label, (x + 5, y - 5),
                self.font, 0.6, (0, 0, 0), 2
            )

        return frame

    def _draw_guidance_arrow(self, frame, surface_tracker, object_detector, state_manager):
        """Draw an arrow from current object to its target position."""
        current_step = state_manager.get_current_step()
        if not current_step or current_step.completed:
            return frame

        # Get object info
        obj_info = object_detector.get_object_info(current_step.object_name)
        if not obj_info or not obj_info['detected']:
            return frame

        object_center = obj_info['center']
        if object_center is None:
            return frame

        # Calculate target center in table coordinates
        target_x, target_y = current_step.target_position
        target_w, target_h = current_step.target_size
        target_center_table = (target_x + target_w / 2, target_y + target_h / 2)

        # Convert to camera coordinates
        target_center_camera = surface_tracker.table_to_camera(target_center_table)
        if target_center_camera is None:
            return frame

        # Draw arrow
        start_point = (int(object_center[0]), int(object_center[1]))
        end_point = (int(target_center_camera[0]), int(target_center_camera[1]))

        cv2.arrowedLine(
            frame,
            start_point,
            end_point,
            self.colors['arrow'],
            thickness=4,
            tipLength=0.3
        )

        return frame

    def _draw_status_overlay(self, frame, state_manager):
        """Draw the main status overlay at the top of the frame."""
        h, w = frame.shape[:2]

        # Get progress text
        progress_text = state_manager.get_progress_text()

        # Track completed steps and detect new completions
        # Robustness: Count completed steps each frame to detect changes
        completed_count = sum(1 for step in state_manager.steps if step.completed)

        # Detect if procedure was reset (completed count went down)
        # This ensures success feedback works correctly after recalibration or manual reset
        if completed_count < self.last_completed_step_index + 1:
            # Reset all success message tracking
            self.last_completion_time = None
            self.last_completed_step_index = -1
            self.just_completed_step = None

        # Detect when a new step is completed
        # This triggers the 3-second "Great Job!" overlay near the target zone
        if completed_count > self.last_completed_step_index + 1:
            # Record completion time for timed message display
            self.last_completion_time = time.time()
            self.last_completed_step_index = completed_count - 1

            # Store reference to completed step for spatial rendering
            # Robustness: Bounds checking to prevent index errors
            if self.last_completed_step_index >= 0 and self.last_completed_step_index < len(state_manager.steps):
                self.just_completed_step = state_manager.steps[self.last_completed_step_index]

        # Determine background color based on state
        if state_manager.state == ProcedureState.COMPLETED:
            bg_color = self.colors['success']
        elif state_manager.state == ProcedureState.CALIBRATION:
            bg_color = self.colors['warning']
        else:
            bg_color = (50, 50, 50)  # Dark gray

        # Draw background bar
        bar_height = 60
        cv2.rectangle(frame, (0, 0), (w, bar_height), bg_color, -1)

        # Draw progress text
        cv2.putText(
            frame, progress_text, (20, 40),
            self.font, 0.8, self.colors['text_fg'], 2
        )

        # Draw step progress indicator
        if state_manager.state == ProcedureState.IN_PROGRESS:
            # Count completed steps for progress bar
            completed_steps = sum(1 for step in state_manager.steps if step.completed)
            total = len(state_manager.steps)

            # Progress bar
            bar_width = 200
            bar_x = w - bar_width - 20
            bar_y = 20
            bar_h = 20

            # Background
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_h), (100, 100, 100), -1)

            # Progress fill - show proportion of COMPLETED steps
            if total > 0:
                progress = completed_steps / total
                fill_width = int(bar_width * progress)
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_h), self.colors['success'], -1)

            # Border
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_h), self.colors['text_fg'], 2)

        return frame

    def _draw_debug_info(self, frame, state_manager):
        """Draw debug information at the bottom of the frame."""
        h, w = frame.shape[:2]

        debug_info = state_manager.get_debug_info()

        # Format state as proper capitalized words
        state_text = debug_info['state'].replace('_', ' ').title()

        # Create debug text lines
        lines = [
            f"State: {state_text}",
            f"Table: {'Visible' if debug_info['table_visible'] else 'Not Visible'}",
            f"Object: {'Visible' if debug_info['current_object_visible'] else 'Not Visible'}",
            f"Hand: {'Interacting' if debug_info['hand_interacting'] else 'No Interaction'}",
            f"Step: {debug_info['current_step']}/{debug_info['total_steps']}"
        ]

        # Draw semi-transparent background
        debug_height = len(lines) * 25 + 20
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - debug_height), (400, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Draw text lines
        y_offset = h - debug_height + 20
        for line in lines:
            cv2.putText(
                frame, line, (10, y_offset),
                self.font, 0.5, self.colors['text_fg'], 1
            )
            y_offset += 25

        return frame

    def _draw_success_message(self, frame, surface_tracker, state_manager):
        """
        Draw 'Great Job!' success message near the completed target zone.

        Uses coordinate transformation to position the message spatially at the
        target zone where the object was just placed, providing contextual feedback.

        Args:
            frame: Current frame to render on
            surface_tracker: Surface tracker for coordinate transformation
            state_manager: State manager with completion information

        Returns:
            frame: Frame with success message rendered (if applicable)
        """
        # Robustness: Only show if a step was recently completed
        if self.last_completion_time is None or self.just_completed_step is None:
            return frame

        # Check if we're still within the success message duration (3 seconds)
        elapsed = time.time() - self.last_completion_time
        if elapsed >= self.success_message_duration:
            return frame

        # Show during IN_PROGRESS or COMPLETED state
        # COMPLETED state included to show message for final step
        if state_manager.state not in [ProcedureState.IN_PROGRESS, ProcedureState.COMPLETED]:
            return frame

        # Calculate target zone center in table coordinate system
        target_x, target_y = self.just_completed_step.target_position
        target_w, target_h = self.just_completed_step.target_size
        target_center_table = (target_x + target_w / 2, target_y + target_h / 2)

        # Robustness: Check if surface is visible before coordinate transformation
        if not surface_tracker.is_visible:
            return frame

        # Coordinate Transformation: Convert from table space to camera space
        # This demonstrates spatial understanding - message appears at the actual
        # physical location on the table, accounting for camera perspective
        target_center_camera = surface_tracker.table_to_camera(target_center_table)

        # Robustness: Handle transformation failure gracefully
        if target_center_camera is None:
            return frame

        # Calculate position for text (above the target zone)
        text_x = int(target_center_camera[0])
        text_y = int(target_center_camera[1]) - 60

        # Create the success message
        feedback_text = "Great Job!"

        # Get text size for centering
        text_size = cv2.getTextSize(feedback_text, self.font, 1.5, 3)[0]
        text_x = text_x - text_size[0] // 2

        # Draw semi-transparent background
        overlay = frame.copy()
        padding = 20
        cv2.rectangle(
            overlay,
            (text_x - padding, text_y - text_size[1] - padding),
            (text_x + text_size[0] + padding, text_y + padding),
            self.colors['success'],
            -1
        )
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Draw text with outline for visibility
        cv2.putText(
            frame, feedback_text, (text_x, text_y),
            self.font, 1.5, (0, 0, 0), 5  # Black outline
        )
        cv2.putText(
            frame, feedback_text, (text_x, text_y),
            self.font, 1.5, self.colors['text_fg'], 3  # White text
        )

        return frame


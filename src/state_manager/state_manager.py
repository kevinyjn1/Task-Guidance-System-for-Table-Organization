"""
State Manager
Manages the procedure workflow, task progress, and system state.
"""

import json
import cv2
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional


class ProcedureState(Enum):
    """Enumeration of possible procedure states."""
    CALIBRATION = "calibration"
    INITIALIZATION = "initialization"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TaskStep:
    """
    Represents a single step in the procedure.
    """
    step_id: int
    object_name: str
    target_position: Tuple[float, float]  # (x, y) in table coordinates
    target_size: Tuple[float, float]      # (width, height) in table coordinates
    completed: bool = False
    description: str = ""

    def is_object_in_target(self, object_position, tolerance=50):
        """
        Check if object is within the target zone.

        Args:
            object_position: (x, y) tuple in table coordinates
            tolerance: Distance tolerance in pixels

        Returns:
            bool: True if object is within target zone
        """
        if object_position is None:
            return False

        obj_x, obj_y = object_position
        target_x, target_y = self.target_position
        target_w, target_h = self.target_size

        # Check if object center is within target bounding box (with tolerance)
        in_x_range = (target_x - tolerance) <= obj_x <= (target_x + target_w + tolerance)
        in_y_range = (target_y - tolerance) <= obj_y <= (target_y + target_h + tolerance)

        return in_x_range and in_y_range


class StateManager:
    """
    Manages the overall state of the task guidance system.
    Tracks procedure progress, visibility, interaction status, and completion.
    """

    def __init__(self, procedure_config_path=None):
        """
        Initialize the state manager.

        Args:
            procedure_config_path: Path to JSON configuration file for the procedure
        """
        self.state = ProcedureState.CALIBRATION
        self.steps: List[TaskStep] = []
        self.current_step_index = 0

        # System visibility states
        self.table_visible = False
        self.current_object_visible = False

        # Interaction states
        self.hand_interacting = False
        self.object_being_moved = False

        # Completion tracking
        self.procedure_complete = False

        # Load procedure configuration
        if procedure_config_path:
            self.load_procedure(procedure_config_path)

        # Tracking for movement detection
        self.previous_object_positions = {}
        self.movement_threshold = 10  # pixels

        # Workspace tracking
        self.surface_tracker_ref = None

    def load_procedure(self, config_path):
        """
        Load procedure steps from a JSON configuration file.

        Args:
            config_path: Path to the JSON config file
        """
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.steps = []
        for i, step_data in enumerate(config['steps']):
            step = TaskStep(
                step_id=i,
                object_name=step_data['object'],
                target_position=tuple(step_data['target_position']),
                target_size=tuple(step_data['target_size']),
                description=step_data.get('description', f"Move {step_data['object']} to target")
            )
            self.steps.append(step)

    def update(self, surface_tracker, object_detector, hand_tracker):
        """
        Update the state based on current perception data.

        Args:
            surface_tracker: SurfaceTracker instance
            object_detector: ObjectDetector instance
            hand_tracker: HandTracker instance
        """
        # Store surface tracker reference for workspace checks
        self.surface_tracker_ref = surface_tracker

        # Update table visibility
        self.table_visible = surface_tracker.is_visible

        if not self.table_visible:
            # Reset visibility states when table not visible
            self.current_object_visible = False
            self.hand_interacting = False
            return

        # Handle state transitions
        if self.state == ProcedureState.CALIBRATION:
            # Move to initialization once table is visible
            if self.table_visible:
                self.state = ProcedureState.INITIALIZATION

        elif self.state == ProcedureState.INITIALIZATION:
            # Wait for all objects to be detected
            all_objects_detected = all(
                object_detector.is_object_detected(step.object_name)
                for step in self.steps
            )
            if all_objects_detected:
                self.state = ProcedureState.IN_PROGRESS

        elif self.state == ProcedureState.IN_PROGRESS:
            self._update_current_step(surface_tracker, object_detector, hand_tracker)

            # Check if all steps are completed
            if all(step.completed for step in self.steps):
                self.state = ProcedureState.COMPLETED
                self.procedure_complete = True

    def _update_current_step(self, surface_tracker, object_detector, hand_tracker):
        """Update the current step's state."""
        if self.current_step_index >= len(self.steps):
            return

        current_step = self.steps[self.current_step_index]

        # Check if current object is visible AND detected
        obj_info = object_detector.get_object_info(current_step.object_name)
        is_detected = obj_info is not None and obj_info.get('detected', False)

        # Get object position in camera coordinates
        camera_position = obj_info.get('center') if obj_info else None

        # Check if object is inside workspace
        is_in_workspace = self.is_point_in_workspace(camera_position) if camera_position else False

        # Update visibility: object must be detected AND inside workspace
        self.current_object_visible = is_detected and is_in_workspace

        if not self.current_object_visible:
            # Reset interaction states when object not visible
            self.hand_interacting = False
            self.object_being_moved = False
            return

        # Convert to table coordinates
        table_position = surface_tracker.camera_to_table(camera_position)

        if table_position is None:
            self.current_object_visible = False
            self.hand_interacting = False
            self.object_being_moved = False
            return

        # Check if hand is interacting with object
        # Only if hands are detected and in workspace
        if hand_tracker.hands_detected:
            self.hand_interacting = hand_tracker.is_hand_near_object(camera_position, threshold=100)
        else:
            self.hand_interacting = False

        # Detect object movement
        self.object_being_moved = self._is_object_moving(
            current_step.object_name,
            camera_position
        )

        # Check if step is completed
        if current_step.is_object_in_target(table_position, tolerance=40):
            if not current_step.completed:
                current_step.completed = True
                # Move to next step
                self.current_step_index += 1

    def _is_object_moving(self, object_name, current_position):
        """
        Detect if an object is currently being moved.

        Args:
            object_name: Name of the object
            current_position: Current (x, y) position

        Returns:
            bool: True if object appears to be moving
        """
        if current_position is None:
            return False

        if object_name not in self.previous_object_positions:
            self.previous_object_positions[object_name] = current_position
            return False

        prev_x, prev_y = self.previous_object_positions[object_name]
        curr_x, curr_y = current_position

        distance = np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)

        self.previous_object_positions[object_name] = current_position

        return distance > self.movement_threshold

    def get_current_step(self) -> Optional[TaskStep]:
        """
        Get the current active step.

        Returns:
            TaskStep or None if all steps completed
        """
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def get_progress_text(self) -> str:
        """
        Get a text description of the current progress.

        Returns:
            str: Progress description
        """
        if self.state == ProcedureState.CALIBRATION:
            return "Calibrating... Please ensure AprilTag markers are visible"

        elif self.state == ProcedureState.INITIALIZATION:
            return "Initialization... Place all objects on the table"

        elif self.state == ProcedureState.IN_PROGRESS:
            current_step = self.get_current_step()
            if current_step:
                step_num = self.current_step_index + 1
                total_steps = len(self.steps)
                return f"Step {step_num}/{total_steps}: {current_step.description}"
            return "Processing..."

        elif self.state == ProcedureState.COMPLETED:
            return "Table Set Successfully! All tasks completed."

        return "Unknown state"

    def get_debug_info(self) -> dict:
        """
        Get debug information about the current state.

        Returns:
            dict: Debug information
        """
        current_step = self.get_current_step()

        # When completed, show total_steps/total_steps instead of N/A
        if self.procedure_complete or self.state == ProcedureState.COMPLETED:
            current_step_display = len(self.steps)
        else:
            current_step_display = self.current_step_index + 1 if current_step else 'N/A'

        return {
            'state': self.state.value,
            'table_visible': self.table_visible,
            'current_object_visible': self.current_object_visible,
            'hand_interacting': self.hand_interacting,
            'object_being_moved': self.object_being_moved,
            'current_step': current_step_display,
            'total_steps': len(self.steps),
            'procedure_complete': self.procedure_complete
        }

    def get_full_status(self) -> dict:
        """
        Get comprehensive status for all state management requirements.

        Returns:
            dict: Complete status including procedure progress, visibility,
                  interaction status, and completion status
        """
        current_step = self.get_current_step()

        return {
            # A. Procedure Progress
            'procedure_progress': {
                'current_step_number': self.current_step_index + 1 if current_step else 'N/A',
                'total_steps': len(self.steps),
                'current_step_description': current_step.description if current_step else 'N/A',
                'progress_text': self.get_progress_text(),
                'state': self.state.value
            },

            # B. Visibility
            'visibility': {
                'table_surface_visible': self.table_visible,
                'target_object_detected': self.current_object_visible,
                'target_object_name': current_step.object_name if current_step else 'N/A'
            },

            # C. Interaction Status (inferred)
            'interaction_status': {
                'hand_near_object': self.hand_interacting,
                'object_moving': self.object_being_moved,
                'user_is_moving_item': self.hand_interacting or self.object_being_moved  # Inferred
            },

            # D. Completion Status
            'completion_status': {
                'current_step_complete': current_step.completed if current_step else True,
                'procedure_complete': self.procedure_complete,
                'completed_steps': sum(1 for step in self.steps if step.completed),
                'remaining_steps': sum(1 for step in self.steps if not step.completed)
            }
        }

    def reset(self):
        """Reset the state manager to initial state."""
        self.state = ProcedureState.CALIBRATION
        self.current_step_index = 0
        self.table_visible = False
        self.current_object_visible = False
        self.hand_interacting = False
        self.object_being_moved = False
        self.procedure_complete = False
        self.previous_object_positions = {}

        for step in self.steps:
            step.completed = False

    def is_point_in_workspace(self, point):
        """
        Check if a point (in camera coordinates) is inside the workspace boundary.

        Args:
            point: (x, y) tuple in camera coordinates

        Returns:
            bool: True if point is inside workspace
        """
        if point is None or self.surface_tracker_ref is None:
            return False

        if not self.surface_tracker_ref.is_visible:
            return False

        # Get table boundary points
        boundary = self.surface_tracker_ref.get_table_boundary_points()
        if boundary is None:
            return False

        # Use cv2.pointPolygonTest to check if point is inside polygon
        result = cv2.pointPolygonTest(boundary.astype(np.int32), point, False)
        return result >= 0  # >= 0 means inside or on boundary

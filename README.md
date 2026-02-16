# Physical Task Guidance System - Table Organization

A real-time computer vision system that guides users through organizing objects on a table using augmented reality overlays, AprilTag surface tracking, and hybrid object detection.

## Project Overview

This system uses an Intel RealSense D435i camera to guide users through a 3-step table organization task. It detects a workspace defined by AprilTag markers, identifies objects (bottle, tape, block), and provides real-time visual guidance (arrows, target zones, progress feedback) to help users place each object in its designated location.

**Project**: #9 - Physical Task Guidance System (Option 2: Table Organization)

## System Architecture

The system is built with three core modules that communicate through well-defined interfaces:

```mermaid
graph TB
    Frame[Camera Frame] --> ST[Surface Tracker]
    Frame --> OD[Object Detector]
    Frame --> HT[Hand Tracker]
    
    ST --> SM[State Manager]
    OD --> SM
    HT --> SM
    
    SM --> RN[Renderer]
    ST --> RN
    OD --> RN
    HT --> RN
    
    RN --> Output[Display Frame]
    
    style Frame fill:#fff,stroke:#2196F3,stroke-width:2px,color:#000
    style Output fill:#fff,stroke:#4CAF50,stroke-width:2px,color:#000
    style ST fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
    style OD fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#000
    style HT fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
    style SM fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    style RN fill:#EDE7F6,stroke:#7B1FA2,stroke-width:2px,color:#000
```

### Module Communication
- **Perception → State Manager**: Object positions and hand tracking data flow to the state manager for logic updates
- **State Manager → Renderer**: Task progress, step info, and completion status flow to the renderer for visual feedback
- **Perception → Renderer**: Surface tracker provides coordinate transformations for perspective-correct rendering

## Features

### A. Perception Module
- **Surface/Table Tracking**: AprilTag markers (tag36h11, IDs 0-3) define the workspace boundary and compute a homography matrix for coordinate transformation between table space and camera space
- **Object Detection (Hybrid)**: YOLOv8 for common objects (bottle) + HSV color segmentation for custom objects (tape, blocks). Only objects inside the workspace boundary are tracked.
- **Hand Tracking (Bonus)**: MediaPipe Hands detects user hands and interaction with objects (confidence threshold: 0.3)

```mermaid
flowchart TB
    Frame[Camera Frame] --> ST
    Frame --> OD
    Frame --> HT
    
    subgraph ST[Surface Tracker]
        ST1[Grayscale] --> ST2[Detect AprilTags]
        ST2 --> ST3{4 Found?}
        ST3 -->|Yes| ST4[Compute Homography]
        ST3 -->|No| ST5[visible = false]
    end
    
    subgraph OD[Object Detector]
        OD1{Type?}
        OD1 -->|bottle| OD2[YOLO v8]
        OD1 -->|tape/block| OD3[HSV Color]
        OD3 --> OD4[Find Contours]
    end
    
    subgraph HT[Hand Tracker]
        HT1[RGB Convert] --> HT2[MediaPipe]
        HT2 --> HT3{Hands?}
        HT3 -->|Yes| HT4[Get Centers]
        HT3 -->|No| HT5[detected = false]
    end
    
    ST4 --> Out1[Homography Matrix]
    ST5 --> Out1
    OD2 --> Out2[Object Positions]
    OD4 --> Out2
    HT4 --> Out3[Hand Positions]
    HT5 --> Out3
    
    Out1 --> SM[State Manager]
    Out2 --> SM
    Out3 --> SM
    
    style Frame fill:#fff,stroke:#2196F3,stroke-width:2px,color:#000
    style SM fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    style Out1 fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
    style Out2 fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
    style Out3 fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
    style ST fill:#E3F2FD,stroke:#1976D2,color:#000
    style OD fill:#FFF3E0,stroke:#E65100,color:#000
    style HT fill:#F3E5F5,stroke:#7B1FA2,color:#000
```

### B. State Management Module
- **Procedure Progress**: Tracks current step (1/3, 2/3, 3/3), step descriptions, and overall progress
- **Visibility**: Monitors table surface visibility and object positions within workspace boundary (using `cv2.pointPolygonTest`). Automatically updates to "not visible" when objects leave the workspace or are not detected.
- **Interaction Status**: Detects hand proximity to objects and object movement. Resets automatically when hands are not detected.
- **Completion Status**: Validates when objects are placed within target zones. Tracks per-step and overall procedure completion.

```mermaid
flowchart TD
    Start([Update]) --> TableVis{Table Visible?}
    
    TableVis -->|No| Reset[Reset States]
    Reset --> End([Return])
    
    TableVis -->|Yes| State{Current State?}
    
    State -->|CALIBRATION| S1[Calibration]
    S1 --> C1{Table OK?}
    C1 -->|Yes| T1[Go to INIT]
    C1 -->|No| End
    T1 --> End
    
    State -->|INITIALIZATION| S2[Initialization]
    S2 --> C2{All Objects?}
    C2 -->|Yes| T2[Go to IN_PROGRESS]
    C2 -->|No| End
    T2 --> End
    
    State -->|IN_PROGRESS| S3[In Progress]
    S3 --> C3{Object Visible?}
    C3 -->|No| R2[Reset Interaction]
    R2 --> End
    C3 -->|Yes| C4{Hand Near?}
    C4 -->|Yes| H1[hand_interacting = true]
    C4 -->|No| H2[hand_interacting = false]
    H1 --> C5{In Target Zone?}
    H2 --> C5
    C5 -->|Yes| Done[Mark Complete]
    C5 -->|No| End
    Done --> C6{All Done?}
    C6 -->|Yes| T3[Go to COMPLETED]
    C6 -->|No| End
    T3 --> End
    
    State -->|COMPLETED| S4[Completed]
    S4 --> End
    
    style Start fill:#fff,stroke:#4CAF50,stroke-width:2px,color:#000
    style End fill:#fff,stroke:#9E9E9E,stroke-width:2px,color:#000
    style State fill:#FFF9C4,stroke:#F9A825,stroke-width:2px,color:#000
    style C5 fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    style Done fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
```

### C. Visualization & Interface
- **Workspace Boundary**: Yellow polygon drawn from AprilTag marker positions
- **Object Highlighting**: Green bounding boxes for detected objects, magenta for the current target object
- **Target Zones**: Perspective-corrected zones rendered via homography transformation (orange = incomplete, green = complete)
- **Guidance Arrows**: Magenta arrows from current object to its target location
- **Success Feedback**: "Great Job!" overlay appears at the target zone for 3 seconds upon step completion
- **Status Overlay**: Top bar with progress text and a progress bar showing completed steps
- **Debug Info**: Bottom-left panel showing real-time system state (State, Table, Object, Hand, Step)

```mermaid
flowchart TD
    Start([Input Frame]) --> L1
    
    L1[Layer 1: Table Boundary] --> L2
    L2[Layer 2: Target Zones] --> L3
    L3[Layer 3: Object Boxes] --> L4
    L4[Layer 4: Guidance Arrow] --> L5
    L5[Layer 5: Hand Skeleton] --> L6
    L6[Layer 6: Status Bar] --> L7
    L7[Layer 7: Debug Panel] --> L8
    L8[Layer 8: Success Message] --> Output
    
    Output([Output Frame])
    
    style Start fill:#fff,stroke:#2196F3,stroke-width:2px,color:#000
    style Output fill:#fff,stroke:#4CAF50,stroke-width:2px,color:#000
    style L1 fill:#FFF9C4,stroke:#F9A825,stroke-width:2px,color:#000
    style L2 fill:#FFE0B2,stroke:#E65100,stroke-width:2px,color:#000
    style L3 fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
    style L4 fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    style L5 fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
    style L6 fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
    style L7 fill:#F5F5F5,stroke:#616161,stroke-width:2px,color:#000
    style L8 fill:#DCEDC8,stroke:#689F38,stroke-width:2px,color:#000
```

### Coordinate Transformation

The system maps between two coordinate spaces using a homography matrix computed from the 4 AprilTag marker positions:
- **Table Coordinates** (800x600): Stable physical coordinates on the table surface, not affected by camera angle
- **Camera Coordinates**: Pixel coordinates in the camera frame

```mermaid
flowchart LR
    subgraph Physical[Physical World]
        P1[AprilTags]
        P2[Objects]
    end
    
    subgraph Camera[Camera Space]
        C1[Marker Corners]
        C2[Object Centers]
    end
    
    subgraph Table[Table Space]
        T1[800x600 Grid]
        T2[Target Zones]
    end
    
    P1 --> C1
    P2 --> C2
    
    C1 --> H[Homography H]
    
    C2 -->|camera_to_table| T1
    T2 -->|table_to_camera| R1[Render Points]
    
    R1 --> Final[Perspective Overlay]
    T1 --> Logic[Completion Check]
    
    style H fill:#FFF9C4,stroke:#F9A825,stroke-width:2px,color:#000
    style Final fill:#C8E6C9,stroke:#388E3C,stroke-width:2px,color:#000
    style Logic fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    style Physical fill:#E3F2FD,stroke:#1976D2,color:#000
    style Camera fill:#FFF3E0,stroke:#E65100,color:#000
    style Table fill:#F3E5F5,stroke:#7B1FA2,color:#000
```

This enables perspective-correct rendering of target zones that align with the physical table surface regardless of camera position or angle.

## Main Loop

```mermaid
flowchart TD
    Start([Start]) --> Init[Initialize Components]
    Init --> Config[Load Config]
    Config --> Cam{RealSense?}
    
    Cam -->|Yes| RS[RealSense Camera]
    Cam -->|No| WC[Webcam]
    
    RS --> Loop
    WC --> Loop
    
    Loop{Main Loop} --> Frame[Get Frame]
    Frame --> P1[Update Surface Tracker]
    P1 --> P2[Update Object Detector]
    P2 --> P3[Update Hand Tracker]
    P3 --> P4[Update State Manager]
    P4 --> P5[Render Frame]
    P5 --> Show[Display]
    Show --> Key{Key Press?}
    
    Key -->|q| Exit([Exit])
    Key -->|r| Reset[Reset]
    Key -->|c| Calib[Recalibrate]
    Key -->|d| Debug[Toggle Debug]
    Key -->|None| Loop
    
    Reset --> Loop
    Calib --> Loop
    Debug --> Loop
    
    style Start fill:#fff,stroke:#4CAF50,stroke-width:2px,color:#000
    style Exit fill:#fff,stroke:#f44336,stroke-width:2px,color:#000
    style Loop fill:#FFF9C4,stroke:#F9A825,stroke-width:2px,color:#000
    style P4 fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    style P5 fill:#EDE7F6,stroke:#7B1FA2,stroke-width:2px,color:#000
```

## Hardware Requirements

- Intel RealSense D435i camera (or compatible USB camera)
- 4 printed AprilTag markers (tag36h11 family, IDs 0, 1, 2, 3)
- Objects: bottle, masking tape, 3D-printed block (or similar colored objects)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd table_organization_guidance
```

### 2. Set Up Virtual Environment
A Python 3.12 virtual environment is required (MediaPipe 0.10.14 requires Python <= 3.12):
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

Dependencies:
| Package | Purpose |
|---------|---------|
| `opencv-contrib-python` | Computer vision, image processing |
| `numpy` | Array operations, coordinate math |
| `pyrealsense2` | Intel RealSense camera interface |
| `pupil-apriltags` | AprilTag detection (tag36h11 family) |
| `ultralytics` | YOLOv8 object detection (bottle) |
| `mediapipe` | Hand tracking (bonus feature) |

### 4. Prepare AprilTag Markers
- Download markers from: https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11
- Print markers: `tag36_11_00000.png` through `tag36_11_00003.png`
- Place at table corners:
  - **ID 0**: Top-left
  - **ID 1**: Top-right
  - **ID 2**: Bottom-right
  - **ID 3**: Bottom-left

## Running the System

### Quick Start
```bash
./run.sh
```

### Manual Start
```bash
source .venv/bin/activate
cd src
python main.py
```

### Keyboard Controls
| Key | Action |
|-----|--------|
| `q` | Quit the application |
| `r` | Reset the procedure (start over) |
| `c` | Recalibrate (re-detect markers) |
| `s` | Print full state status to console |

## Procedure Config

The task steps are defined in [`config/procedure_config.json`](config/procedure_config.json):

```json
{
  "procedure_name": "Table Organization - Object Placement",
  "steps": [
    {
      "object": "bottle",
      "target_position": [150, 100],
      "target_size": [100, 150],
      "description": "Move the Bottle to the upper left"
    },
    {
      "object": "tape",
      "target_position": [350, 200],
      "target_size": [120, 80],
      "description": "Move the Tape to the center"
    },
    {
      "object": "block",
      "target_position": [550, 150],
      "target_size": [100, 100],
      "description": "Move the Block to the right"
    }
  ],
  "markers": {
    "type": "apriltag",
    "family": "tag36h11",
    "ids": [0, 1, 2, 3]
  },
  "settings": {
    "completion_tolerance": 40,
    "hand_interaction_threshold": 100,
    "movement_threshold": 10
  }
}
```

Target positions, sizes, object names, and tolerance settings are all customizable through this config file.

## Task Workflow

1. **Calibration**: System starts with an empty table. All 4 AprilTag markers must be visible to detect the workspace boundary.

2. **Initialization**: 3 target zones are generated on the table. The user places the objects (bottle, tape, block) randomly on the table.

3. **Task 1 (Bottle)**: System highlights the bottle with a magenta bounding box and draws a guidance arrow pointing to Target Location A. Once the bottle is within the target zone, the zone turns green and "Great Job!" is displayed near the target area for 3 seconds.

4. **Task 2 (Tape)**: System highlights the tape and draws an arrow to Target Location B. Zone turns green and "Great Job!" displays when tape is placed correctly.

5. **Task 3 (Block)**: System highlights the block and draws an arrow to Target Location C. Zone turns green and "Great Job!" displays when block is placed correctly.

6. **Completion**: Once all items are placed, the system displays "Table Set Successfully!" with a full progress bar.

## Color Calibration

If tape or blocks aren't being detected correctly, use the color calibration utility:

```bash
source .venv/bin/activate
cd src
python calibrate_hybrid_colors.py
```

- Press `1`/`2` to select tape or block
- Click on the object multiple times (5-10 points)
- Press `SPACE` to apply calibration
- Press `S` to output the calibrated color ranges (copy into `main.py`)

## Project Structure

```
table_organization_guidance/
├── README.md                          # This documentation
├── requirements.txt                   # Python dependencies
├── run.sh                             # Convenience run script (activates venv)
├── config/
│   └── procedure_config.json          # Task step definitions and settings
└── src/
    ├── main.py                        # Main application entry point
    ├── calibrate_hybrid_colors.py     # Color calibration utility for tape/block
    ├── yolov8n.pt                     # YOLOv8 nano model weights
    ├── perception/                    # Perception Module
    │   ├── surface_tracker.py         # AprilTag detection and homography transformation
    │   ├── hybrid_detector.py         # Hybrid detector combining YOLO + color-based detection
    │   ├── object_detector.py         # Color-based object detection (HSV segmentation)
    │   └── hand_tracker.py            # MediaPipe hand tracking
    ├── state_manager/                 # State Management Module
    │   └── state_manager.py           # Procedure logic, step tracking, workspace boundary checks
    └── visualization/                 # Visualization Module
        └── renderer.py                # All visual overlays, target zones, arrows, status, debug info
```

## Robustness

The system handles common failure cases gracefully without crashing:
- **Object occlusion**: If an object briefly disappears or is occluded, the system continues and automatically updates visibility state to "Not Visible"
- **Marker loss**: If AprilTag markers are temporarily occluded, the system falls back to calibration mode and recovers when markers reappear
- **Hand tracking**: Optional module - system works fully without hands detected; interaction states reset automatically
- **Workspace filtering**: Only objects within the AprilTag boundary are tracked, preventing false detections outside the workspace
- **State resets**: When objects leave the workspace or hands are removed, interaction and movement states reset automatically

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Markers not detected | Ensure all 4 markers visible, check lighting, make markers larger |
| Objects not detected | Run `calibrate_hybrid_colors.py` to tune color ranges for your objects |
| Hand tracking not working | Ensure MediaPipe is installed, check lighting conditions |
| MediaPipe import error | Use the `.venv` virtual environment (Python 3.12 required) |

## Demo Video

A demo video is included showing the complete workflow: calibration, object placement, guided organization through all 3 steps, "Great Job!" feedback, and final completion screen.

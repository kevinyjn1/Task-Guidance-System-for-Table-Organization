# Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd table_organization_guidance
pip install -r requirements.txt
```

### 2. Prepare AprilTag Markers

You need to print 4 AprilTag markers from the **tag36h11** family:
- Tag ID 0 (Top-Left corner)
- Tag ID 1 (Top-Right corner)
- Tag ID 2 (Bottom-Right corner)
- Tag ID 3 (Bottom-Left corner)

#### Where to Get the Markers:

**Option 1: Download from GitHub**
Visit: https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11

Download these files:
- `tag36_11_00000.png` → Print as Marker 0
- `tag36_11_00001.png` → Print as Marker 1
- `tag36_11_00002.png` → Print as Marker 2
- `tag36_11_00003.png` → Print as Marker 3

**Option 2: Generate Programmatically**
```python
# Run this in Python to get marker info
from utils.helpers import generate_apriltag_info
print(generate_apriltag_info())
```

#### Printing Tips:
- Print on white paper (not glossy)
- Recommended size: 5-10 cm per marker
- Leave white border around each marker when cutting
- Keep markers flat (can laminate or attach to cardboard)

### 3. Setup Your Table

1. Place the 4 printed markers at the corners of your working area:
   ```
   [0]---------------[1]
    |                 |
    |   Work Area     |
    |                 |
   [3]---------------[2]
   ```

2. Ensure markers are:
   - Flat and not wrinkled
   - Visible to your webcam
   - Well-lit (avoid shadows and glare)
   - Approximately forming a rectangle

### 4. Prepare Your Objects

You need three colored objects for detection:
- **Cup**: Red colored (or update color range in code)
- **Bottle**: Blue colored (or update color range in code)
- **Plate**: White or light colored (or update color range in code)

**Note**: If your objects are different colors, you can calibrate them by editing the color ranges in `src/perception/object_detector.py`.

### 5. Run the System

```bash
cd src
python main.py
```

Or with custom configuration:
```bash
python main.py --config ../config/procedure_config.json --camera 0
```

### 6. Calibration Process

1. **Step 1**: When you start, the system will be in CALIBRATION mode
   - Ensure all 4 AprilTag markers are visible in the camera
   - System will automatically detect them and switch to INITIALIZATION

2. **Step 2**: INITIALIZATION phase
   - Place your cup, bottle, and plate randomly on the table
   - System will detect them and switch to IN_PROGRESS

3. **Step 3**: Follow the on-screen guidance
   - The system will highlight one object at a time
   - An arrow will point from the object to its target location
   - Move the object to the target zone
   - Zone turns green when correctly placed
   - Repeat for all objects

4. **Completion**: When all objects are placed, you'll see "Table Set Successfully!"

## Keyboard Controls

- `q` - Quit the application
- `r` - Reset procedure (start over)
- `c` - Recalibrate (re-detect markers)

## Troubleshooting

### Markers Not Detected
- **Check visibility**: All 4 markers must be in camera view
- **Check lighting**: Ensure even lighting, no harsh shadows
- **Check flatness**: Markers should be flat, not curved
- **Check size**: Markers might be too small if camera is far away

### Objects Not Detected
- **Check colors**: Object colors must match expected ranges
- **Calibrate colors**: Edit `src/perception/object_detector.py` to adjust HSV ranges
- **Check table boundary**: Objects must be within the marker boundary
- **Check lighting**: Ensure good, even lighting on objects

### Camera Not Found
```bash
# Try different camera IDs
python main.py --camera 1
python main.py --camera 2
```

### Performance Issues
- Reduce camera resolution in `src/main.py`
- Disable hand tracking by commenting out hand tracker updates
- Close other applications using the camera

## Testing Your Setup

### Test 1: Verify Dependencies
```bash
python -c "import cv2, numpy, dt_apriltags, mediapipe; print('All dependencies OK!')"
```

### Test 2: Test Camera
```bash
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK!' if cap.isOpened() else 'Camera FAILED'); cap.release()"
```

### Test 3: Verify Configuration
```bash
python -c "import json; data = json.load(open('config/procedure_config.json')); print(f'Config OK! {len(data[\"steps\"])} steps loaded')"
```

## Customization

### Change Target Positions
Edit `config/procedure_config.json`:
```json
{
  "steps": [
    {
      "object": "cup",
      "target_position": [X, Y],    // Position in table coordinates (0-800, 0-600)
      "target_size": [W, H],        // Size of target zone
      "description": "Move cup here"
    }
  ]
}
```

### Add/Remove Objects
1. Add object detection in `src/perception/object_detector.py`
2. Add steps to `config/procedure_config.json`
3. Adjust color ranges for your specific objects

### Change Colors
Edit `src/perception/object_detector.py`:
```python
self.object_configs = {
    'cup': {
        'color_lower': np.array([H_min, S_min, V_min]),
        'color_upper': np.array([H_max, S_max, V_max]),
        ...
    }
}
```

Use a HSV color picker tool to find the right values for your objects.

## Next Steps

1. Run the system and complete a test procedure
2. Record a demo video showing the full workflow
3. Customize the procedure for your specific use case
4. Experiment with different objects and layouts

## Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Verify all dependencies are installed
3. Ensure markers are properly positioned and visible
4. Check that objects match expected colors

For questions about the project, contact:
- Yuxuan Liu: liurick@umich.edu
- Chen Liang: clumich@umich.edu

# AprilTag Markers Setup

This project uses **AprilTag markers** from the **tag36h11** family to track the table surface.

## Required Markers

You need 4 markers with the following IDs:
- **Tag 0** - Place at Top-Left corner
- **Tag 1** - Place at Top-Right corner
- **Tag 2** - Place at Bottom-Right corner
- **Tag 3** - Place at Bottom-Left corner

## How to Get the Markers

### Option 1: Download from GitHub (Recommended)

Visit the official AprilTag repository:
https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11

Download these specific files:
1. `tag36_11_00000.png` → **Marker 0** (Top-Left)
2. `tag36_11_00001.png` → **Marker 1** (Top-Right)
3. `tag36_11_00002.png` → **Marker 2** (Bottom-Right)
4. `tag36_11_00003.png` → **Marker 3** (Bottom-Left)

Direct links:
- [Tag 0](https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00000.png)
- [Tag 1](https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00001.png)
- [Tag 2](https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00002.png)
- [Tag 3](https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00003.png)

### Option 2: Download All at Once

Clone the entire repository:
```bash
git clone https://github.com/AprilRobotics/apriltag-imgs.git
cd apriltag-imgs/tag36h11
# Use tag36_11_00000.png through tag36_11_00003.png
```

## Printing Instructions

### Recommended Settings
- **Paper**: Standard white printer paper (NOT glossy)
- **Size**: 5-10 cm per marker (larger is easier to detect)
- **Quality**: Print at highest quality setting
- **Border**: Leave at least 1cm white border around each tag

### Printing Steps
1. Open each PNG file in an image viewer
2. Print with these settings:
   - **Scale**: Fit to page or custom size (5-10 cm)
   - **Color**: Black and white is fine
   - **Quality**: Highest/Best
3. Check that the printed tags are sharp and clear
4. Do not fold, wrinkle, or damage the tags

### After Printing
1. Cut out each marker, leaving white border
2. **Optional but recommended**: Laminate or attach to cardboard for durability
3. Label the back of each marker with its ID (0, 1, 2, 3)
4. Keep markers flat and clean

## Placement Guide

Place markers at the corners of your working area:

```
     [Tag 0]-------------------------[Tag 1]
        (TL)                            (TR)
         |                               |
         |                               |
         |        Work Area              |
         |      (Place objects here)     |
         |                               |
         |                               |
        (BL)                            (BR)
     [Tag 3]-------------------------[Tag 2]
```

### Placement Tips
- Markers should form a rectangle (doesn't need to be perfect)
- Keep markers flat against the table
- Ensure all markers are visible to the camera
- Recommended table size: 50cm x 50cm or larger
- Distance between markers: 30-60 cm works well

## Lighting Requirements

For best detection:
- Use even, diffuse lighting
- Avoid direct sunlight or harsh shadows on markers
- Avoid glare or reflections (don't laminate with glossy material)
- If markers aren't detected, try adjusting room lighting

## Troubleshooting

### Markers Not Detected
1. **Check visibility**: All 4 markers must be in camera view
2. **Check lighting**: Ensure even lighting, no shadows
3. **Check focus**: Markers should be in focus (not blurry)
4. **Check size**: If camera is far, markers might appear too small
5. **Check damage**: Markers should be clean and undamaged

### Only Some Markers Detected
- Check if missing markers are in camera view
- Look for shadows or glare on missing markers
- Ensure markers are flat and not curled

### False Detections
- Ensure there are no other AprilTags nearby
- Remove any papers with high-contrast patterns
- Check that markers are from correct family (tag36h11)

## Testing Your Markers

After printing and placing markers:

1. Run the test script:
   ```bash
   python test_installation.py
   ```

2. Run the main application:
   ```bash
   cd src
   python main.py
   ```

3. During calibration:
   - All 4 corners should be detected
   - Yellow lines should connect the markers
   - Corner labels (TL, TR, BR, BL) should appear

## Alternative: Create Your Own Markers (Advanced)

If you want to generate markers programmatically:

```python
# This requires additional setup
import numpy as np
from PIL import Image

# Or use online generators:
# - https://chev.me/arucogen/ (Note: This is for ArUco, not AprilTag)
# - For AprilTag: Use the official images from GitHub
```

**Note**: It's much easier to just download the official pre-generated images from the GitHub repository.

## Reference

- **Family**: tag36h11
- **IDs used**: 0, 1, 2, 3
- **Official repo**: https://github.com/AprilRobotics/apriltag-imgs
- **AprilTag documentation**: https://github.com/AprilRobotics/apriltag

## Quick Setup Checklist

- [ ] Downloaded all 4 marker images (IDs 0, 1, 2, 3)
- [ ] Printed markers on white paper
- [ ] Cut out markers with white border
- [ ] Labeled markers on the back
- [ ] Placed markers at table corners
- [ ] Ensured markers are flat and visible
- [ ] Checked lighting conditions
- [ ] Tested marker detection with the application

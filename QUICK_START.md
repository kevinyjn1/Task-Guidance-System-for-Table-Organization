# Quick Start Guide

Get up and running in 5 minutes!

## 1. Install (2 minutes)

```bash
cd table_organization_guidance
pip install -r requirements.txt
```

## 2. Get Markers (1 minute)

Download these 4 images and print them:
- https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00000.png
- https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00001.png
- https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00002.png
- https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_00003.png

Print them and place at table corners:
```
[0]------[1]
 |        |
 |  TABLE |
 |        |
[3]------[2]
```

## 3. Prepare Objects (1 minute)

Get three colored objects:
- **Red** cup
- **Blue** bottle
- **White** plate

## 4. Run (1 minute)

```bash
cd src
python main.py
```

## 5. Use It!

1. Make sure all 4 markers visible → **Auto-calibrates**
2. Place objects on table → **Auto-detects**
3. Follow the arrows → **Move objects to green zones**
4. Done! → **"Table Set Successfully!"**

## Controls

- `q` = Quit
- `r` = Reset
- `c` = Recalibrate

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't see markers | Adjust camera angle, improve lighting |
| Objects not detected | Use brighter colored objects, check lighting |
| Camera not working | Try `--camera 1` or `--camera 2` |
| Import errors | Run `pip install -r requirements.txt` again |

## Test Your Setup

```bash
python test_installation.py
```

This will check everything is working!

## Need Help?

Read the full docs:
- [README.md](README.md) - Complete documentation
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions
- [APRILTAG_MARKERS.md](APRILTAG_MARKERS.md) - Marker information

---

**That's it!** You should now have a working task guidance system. 🎉

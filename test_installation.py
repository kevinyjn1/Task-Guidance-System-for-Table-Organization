#!/usr/bin/env python3
"""
Installation Test Script
Verifies that all dependencies and components are properly installed.
"""

import sys


def test_dependencies():
    """Test that all required dependencies are available."""
    print("Testing dependencies...")
    print("-" * 50)

    dependencies = {
        'opencv-python': 'cv2',
        'numpy': 'numpy',
        'pupil-apriltags': 'pupil_apriltags',
        'mediapipe': 'mediapipe'
    }

    failed = []

    for package_name, import_name in dependencies.items():
        try:
            __import__(import_name)
            print(f"✓ {package_name}: OK")
        except ImportError as e:
            print(f"✗ {package_name}: MISSING")
            failed.append(package_name)

    print("-" * 50)

    if failed:
        print(f"\nFailed to import: {', '.join(failed)}")
        print("Please install missing dependencies:")
        print(f"  pip install {' '.join(failed)}")
        return False
    else:
        print("\n✓ All dependencies installed successfully!\n")
        return True


def test_camera():
    """Test camera availability."""
    print("Testing camera...")
    print("-" * 50)

    try:
        import cv2
        cap = cv2.VideoCapture(0)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                print(f"✓ Camera 0: OK (Resolution: {w}x{h})")
                cap.release()
                return True
            else:
                print("✗ Camera 0: Cannot read frame")
                cap.release()
                return False
        else:
            print("✗ Camera 0: Cannot open")
            print("  Try different camera IDs: --camera 1, --camera 2, etc.")
            return False

    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False
    finally:
        print("-" * 50 + "\n")


def test_configuration():
    """Test configuration file."""
    print("Testing configuration...")
    print("-" * 50)

    try:
        import json
        from pathlib import Path

        config_path = Path('config/procedure_config.json')

        if not config_path.exists():
            print(f"✗ Configuration file not found: {config_path}")
            return False

        with open(config_path, 'r') as f:
            config = json.load(f)

        if 'steps' not in config:
            print("✗ Configuration missing 'steps' field")
            return False

        num_steps = len(config['steps'])
        print(f"✓ Configuration: OK ({num_steps} steps defined)")

        # Validate each step
        for i, step in enumerate(config['steps']):
            required_fields = ['object', 'target_position', 'target_size']
            missing = [f for f in required_fields if f not in step]

            if missing:
                print(f"  ✗ Step {i}: Missing fields {missing}")
                return False
            else:
                print(f"  ✓ Step {i}: {step['object']} - {step.get('description', 'No description')}")

        print("-" * 50 + "\n")
        return True

    except json.JSONDecodeError as e:
        print(f"✗ Configuration file has invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_modules():
    """Test that project modules can be imported."""
    print("Testing project modules...")
    print("-" * 50)

    # Add src to path
    sys.path.insert(0, 'src')

    modules = {
        'perception.surface_tracker': 'SurfaceTracker',
        'perception.object_detector': 'ObjectDetector',
        'perception.hand_tracker': 'HandTracker',
        'state_manager.state_manager': 'StateManager',
        'visualization.renderer': 'Renderer'
    }

    failed = []

    for module_path, class_name in modules.items():
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✓ {module_path}.{class_name}: OK")
        except ImportError as e:
            print(f"✗ {module_path}: IMPORT ERROR")
            print(f"  {e}")
            failed.append(module_path)
        except AttributeError as e:
            print(f"✗ {module_path}.{class_name}: NOT FOUND")
            failed.append(module_path)

    print("-" * 50 + "\n")

    if failed:
        print(f"Failed to import modules: {', '.join(failed)}")
        return False
    else:
        print("✓ All project modules OK!\n")
        return True


def test_apriltag_detector():
    """Test AprilTag detection capability."""
    print("Testing AprilTag detector...")
    print("-" * 50)

    try:
        from pupil_apriltags import Detector

        detector = Detector(
            families='tag36h11',
            nthreads=1,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0
        )

        print("✓ AprilTag detector initialized successfully")
        print("  Library: pupil_apriltags")
        print("  Family: tag36h11")
        print("  Ready to detect markers: 0, 1, 2, 3")
        print("-" * 50 + "\n")
        return True

    except Exception as e:
        print(f"✗ AprilTag detector failed: {e}")
        print("-" * 50 + "\n")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("TABLE ORGANIZATION GUIDANCE SYSTEM")
    print("Installation Test")
    print("=" * 50 + "\n")

    tests = [
        ("Dependencies", test_dependencies),
        ("Camera", test_camera),
        ("Configuration", test_configuration),
        ("Project Modules", test_modules),
        ("AprilTag Detector", test_apriltag_detector)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}\n")
            results[test_name] = False

    # Summary
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("=" * 50 + "\n")

    if all(results.values()):
        print("✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Print AprilTag markers (IDs 0, 1, 2, 3)")
        print("  2. Place markers at table corners")
        print("  3. Prepare colored objects (red cup, blue bottle, white plate)")
        print("  4. Run: cd src && python main.py")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

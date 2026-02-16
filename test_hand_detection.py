#!/usr/bin/env python3
"""
Simple test for hand detection
"""

import cv2
import mediapipe as mp

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.3,  # Lower threshold for testing
    min_tracking_confidence=0.3
)

# Open camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("="*60)
print("HAND DETECTION TEST")
print("="*60)
print("\nInstructions:")
print("  - Make sure your hands are well-lit")
print("  - Hold your hands in front of the camera")
print("  - Palms should be facing the camera")
print("  - Keep hands within camera view")
print("\nPress 'q' to quit")
print("="*60 + "\n")

frame_count = 0
detection_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to get frame")
            break

        frame_count += 1

        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process
        results = hands.process(rgb_frame)

        # Draw results
        if results.multi_hand_landmarks:
            detection_count += 1
            num_hands = len(results.multi_hand_landmarks)

            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                    mp_draw.DrawingSpec(color=(255, 0, 0), thickness=2)
                )

            # Show detection status
            cv2.putText(
                frame,
                f"HANDS DETECTED: {num_hands}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                3
            )
        else:
            # No hands detected
            cv2.putText(
                frame,
                "NO HANDS DETECTED",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                3
            )

        # Show stats
        if frame_count > 0:
            detection_rate = (detection_count / frame_count) * 100
            cv2.putText(
                frame,
                f"Detection Rate: {detection_rate:.1f}%",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        cv2.imshow('Hand Detection Test', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

except KeyboardInterrupt:
    print("\n\nInterrupted by user")

finally:
    print(f"\nTest Results:")
    print(f"  Total Frames: {frame_count}")
    print(f"  Frames with Hands: {detection_count}")
    if frame_count > 0:
        print(f"  Detection Rate: {(detection_count/frame_count)*100:.1f}%")

    hands.close()
    cap.release()
    cv2.destroyAllWindows()
    print("\nDone!")

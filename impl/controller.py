# controller.py

import cv2
import mediapipe as mp
import time
import threading

# Import shared variables from main_scene
from main_scene import RGBMatrix, RGBMatrixOptions

# ---------------------- Hand Gesture Recognition ----------------------

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands

def recognize_gesture(hand_landmarks):
    """
    Recognize hand gestures based on finger positions:
    - "Start": All four fingers (index, middle, ring, pinky) extended (tips above PIP joints)
    - "Up": Thumb tip is significantly above the wrist
    - "Down": Thumb tip is significantly below the wrist
    - "Neutral": Any other hand position
    """
    # Retrieve landmarks
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]

    # Define a threshold to account for minor movements/noise
    threshold = 0.05  # Adjust this value as needed

    # Check for "Start" Gesture: All four fingers extended
    if (index_tip.y < index_pip.y and
        middle_tip.y < middle_pip.y and
        ring_tip.y < ring_pip.y and
        pinky_tip.y < pinky_pip.y):
        return "Start"

    # Check for "Up" and "Down" Gestures based on thumb position
    thumb_to_wrist_y = thumb_tip.y - wrist.y

    if thumb_to_wrist_y < -threshold:
        return "Up"
    elif thumb_to_wrist_y > threshold:
        return "Down"
    else:
        return "Neutral"

def main_scene_gesture_recognition_thread(matrix, brightness_lock, brightness, active_flag, stop_event):
    """
    Thread function to handle hand gesture recognition.
    Adjusts the brightness of the RGB matrix based on recognized gestures.
    """
    cap = cv2.VideoCapture(0)
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # Adjust as needed
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:
        active = False  # Local state
        last_gesture = "Neutral"
        gesture_start_time = time.time()
        gesture_display_duration = 1  # seconds
        last_brightness_change = time.time()
        debounce_time = 0.3  # seconds

        print("Gesture Recognition Thread Started.")
        print("Waiting for 'Start' gesture (Open Full Hand).")

        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to read frame from webcam.")
                break

            # Convert the frame to RGB as MediaPipe uses RGB images
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process the frame to detect hands
            results = hands.process(rgb_frame)

            # Check for hand landmarks
            if results.multi_hand_landmarks:
                # Process the first detected hand
                hand_landmarks = results.multi_hand_landmarks[0]

                # Recognize gesture
                gesture = recognize_gesture(hand_landmarks)

                # Current time
                current_time = time.time()

                # Handle gestures based on state
                if gesture == "Start" and not active:
                    active = True
                    active_flag.set()
                    print("Recognition started. You can now perform 'Up' and 'Down' gestures.")
                    last_gesture = "Start"
                    gesture_start_time = current_time

                elif active and gesture in ["Up", "Down"]:
                    # To prevent flooding the console, only act if gesture changes or after debounce_time
                    if (gesture != last_gesture) or (current_time - last_brightness_change > debounce_time):
                        print(f"Recognized Gesture: {gesture}")
                        last_gesture = gesture
                        gesture_start_time = current_time
                        last_brightness_change = current_time

                        # Adjust brightness based on gesture
                        with brightness_lock:
                            if gesture == "Up":
                                brightness[0] = min(brightness[0] + 10, 100)  # Increase brightness by 10, max 100
                            elif gesture == "Down":
                                brightness[0] = max(brightness[0] - 10, 0)    # Decrease brightness by 10, min 0
                            # Update the RGB matrix brightness
                            matrix.brightness = brightness[0]
                            print(f"Brightness set to: {brightness[0]}")

            # Limit frame rate to 10 FPS
            time.sleep(0.1)

    cap.release()
    print("Gesture Recognition Thread Exited.")

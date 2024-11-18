### visualisation need to run with monitor

# import cv2
# import mediapipe as mp

# # Initialize MediaPipe Hands and Drawing utilities
# mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils

# # Open the webcam
# cap = cv2.VideoCapture(0)

# # Initialize the Hands module
# with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             print("Failed to grab frame")
#             break
        
#         # Flip the frame horizontally for a mirror view
#         frame = cv2.flip(frame, 1)
        
#         # Convert the frame to RGB (MediaPipe works with RGB images)
#         rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
#         # Process the frame to detect hands
#         results = hands.process(rgb_frame)
        
#         # Draw hand landmarks if detected
#         if results.multi_hand_landmarks:
#             for hand_landmarks in results.multi_hand_landmarks:
#                 mp_drawing.draw_landmarks(
#                     frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
#                 )
        
#         # Display the frame
#         cv2.imshow("Hand Gesture Recognition", frame)
        
#         # Break the loop when 'q' is pressed
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

# # Release the webcam and close OpenCV windows
# cap.release()
# cv2.destroyAllWindows()

## test the controller
import cv2
import mediapipe as mp
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands

# Interpret gestures based on landmarks
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
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]  # Correct attribute

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

def main():
    # Open the webcam
    cap = cv2.VideoCapture(0)

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Initialize the Hands module
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # Adjust as needed
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:
        print("Hand Gesture Recognition Started.")
        print("Waiting for 'Start' gesture (Open Full Hand).")

        active = False  # Indicates whether "Up" and "Down" recognition is active
        last_gesture = "Neutral"
        gesture_start_time = time.time()
        gesture_display_duration = 1  # seconds

        try:
            while True:
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
                        print("Recognition started. You can now perform 'Up' and 'Down' gestures.")
                        last_gesture = "Start"
                        gesture_start_time = current_time

                    elif active and gesture in ["Up", "Down"]:
                        # To prevent flooding the console, only print if gesture changes or after a duration
                        if (gesture != last_gesture) or (current_time - gesture_start_time > gesture_display_duration):
                            print(f"Recognized Gesture: {gesture}")
                            last_gesture = gesture
                            gesture_start_time = current_time

                # To prevent high CPU usage
                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nExiting Hand Gesture Recognition.")

    # Release the webcam
    cap.release()

if __name__ == "__main__":
    main()

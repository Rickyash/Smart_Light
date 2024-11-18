#!/usr/bin/env python3
import cv2
import mediapipe as mp
import time
import sys
import os
import datetime
import threading

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image

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

# ---------------------- LED Matrix Display ----------------------

def preprocess_gif(image_file, matrix_width, matrix_height):
    """
    Preprocess the GIF frames to fit the RGB matrix while maintaining aspect ratio.
    Returns a list of PIL Image frames.
    """
    try:
        gif = Image.open(image_file)
    except IOError:
        sys.exit("Cannot open the provided image. Ensure it's a valid GIF file.")

    # Verify the image is a GIF with multiple frames
    try:
        num_frames = gif.n_frames
    except AttributeError:
        sys.exit("Provided image is not a GIF or does not have multiple frames.")

    if num_frames < 1:
        sys.exit("The GIF has no frames to display.")

    frame_images = []
    print("Preprocessing GIF frames...")
    for frame_index in range(num_frames):
        try:
            gif.seek(frame_index)
            # Copy the frame to avoid modifying the original GIF
            frame = gif.copy()
            # Resize the frame to fit the matrix while maintaining aspect ratio
            frame.thumbnail((matrix_width, matrix_height), Image.LANCZOS)
            # Create a blank canvas and paste the frame onto it centered
            canvas_image = Image.new("RGB", (matrix_width, matrix_height), (0, 0, 0))
            frame_position = (
                (matrix_width - frame.width) // 2,
                (matrix_height - frame.height) // 2
            )
            canvas_image.paste(frame, frame_position)
            # Convert the canvas_image to RGB format
            frame_image = canvas_image.convert("RGB")
            # Append the frame image to the list
            frame_images.append(frame_image)
        except EOFError:
            break  # End of frames
        except Exception as e:
            print(f"Error processing frame {frame_index}: {e}")
    gif.close()
    print("Preprocessing completed.")
    return frame_images

# ---------------------- Gesture Recognition Thread ----------------------

def gesture_recognition_thread(matrix, frame_images, brightness_lock, brightness, active_flag, stop_event):
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

# ---------------------- LED Display Thread ----------------------

def led_display_thread(matrix, frame_images, font, brightness_lock, brightness, active_flag, stop_event):
    num_frames = len(frame_images)
    frame_index = 0

    # Initialize variables for scrolling text
    textColor = graphics.Color(255, 255, 255)
    pos = matrix.width  # Starting position of the text
    y_position = 10     # Vertical position of the text

    print("LED Display Thread Started.")

    while not stop_event.is_set():
        # Create a new frame canvas
        frame_canvas = matrix.CreateFrameCanvas()
        # Get the current frame image
        frame_image = frame_images[frame_index]
        # Set the image onto the frame canvas
        frame_canvas.SetImage(frame_image)
        # Get the current time as text
        current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
        # Draw the text onto the frame canvas
        try:
            text_length = graphics.DrawText(frame_canvas, font, pos, y_position, textColor, current_time_str)
        except Exception as e:
            print(f"Error drawing text: {e}")
            text_length = 0
        # Update text position for scrolling
        pos -= 1
        if (pos + text_length < 0):
            pos = frame_canvas.width
        # Swap the frame canvas onto the matrix
        matrix.SwapOnVSync(frame_canvas)
        # Move to the next frame, looping back to the first frame if necessary
        frame_index = (frame_index + 1) % num_frames
        # Control the frame rate
        time.sleep(0.05)  # 20 FPS

    print("LED Display Thread Exited.")

# ---------------------- Main Integration Function ----------------------

def main():
    # ---------------------- Configuration ----------------------

    # Check for GIF argument
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 combined_hand_led.py <path_to_gif>")
    else:
        image_file = sys.argv[1]
        if not os.path.isfile(image_file):
            sys.exit(f"File not found: {image_file}")

    # Configuration for the RGB matrix
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'  # Adjust if using a different hardware mapping
    options.brightness = 50                   # Initial brightness (0-100)
    options.gpio_slowdown = 4                 # Adjust GPIO slowdown for stability

    # Initialize the RGB matrix
    try:
        matrix = RGBMatrix(options=options)
    except Exception as e:
        sys.exit(f"Failed to initialize RGB Matrix: {e}")

    # Preprocess the GIF frames
    frame_images = preprocess_gif(image_file, matrix.width, matrix.height)

    # Initialize the font
    font = graphics.Font()
    # Adjust the path to your font file if necessary
    font_path = "../res/fonts/7x13.bdf"  # Ensure this path is correct
    if not os.path.isfile(font_path):
        sys.exit(f"Font file not found: {font_path}")
    try:
        font.LoadFont(font_path)
    except Exception as e:
        sys.exit(f"Failed to load font: {e}")

    # Initialize shared variables
    brightness_lock = threading.Lock()
    brightness = [options.brightness]  # Mutable shared variable
    active_flag = threading.Event()
    stop_event = threading.Event()

    # Start gesture recognition thread
    gesture_thread = threading.Thread(target=gesture_recognition_thread, args=(
        matrix, frame_images, brightness_lock, brightness, active_flag, stop_event))
    gesture_thread.start()

    # Start LED display thread
    led_thread = threading.Thread(target=led_display_thread, args=(
        matrix, frame_images, font, brightness_lock, brightness, active_flag, stop_event))
    led_thread.start()

    print("Press CTRL-C to stop.")

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("\nExiting Hand Gesture Recognition and LED Control.")
        stop_event.set()
        gesture_thread.join()
        led_thread.join()
        sys.exit(0)

if __name__ == "__main__":
    main()

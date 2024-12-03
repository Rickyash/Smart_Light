# this one runing sometime it will cause the raspberrypi shut down
import cv2
import mediapipe as mp
import time
import sys
import os
import threading
import asyncio
from io import BytesIO
import requests
import pygame

from pycloudmusic import Music163Api
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

from search_module import search_music_by_voice
from PIL import Image

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands

# ---------------------- Hand Gesture Recognition ----------------------

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

    # Debugging: Print key landmarks
    print(f"Landmarks Debug - Wrist: {wrist.y:.2f}, Thumb: {thumb_tip.y:.2f}, "
          f"Index: {index_tip.y:.2f}, Middle: {middle_tip.y:.2f}, Ring: {ring_tip.y:.2f}, Pinky: {pinky_tip.y:.2f}")

    # Define a threshold to account for minor movements/noise
    threshold = 0.05  # Adjust this value as needed

    # Check for "Start" Gesture: All four fingers extended
    if (index_tip.y < index_pip.y and
        middle_tip.y < middle_pip.y and
        ring_tip.y < ring_pip.y and
        pinky_tip.y < pinky_pip.y):
        print("Detected Gesture: Start (Open Hand)")
        return "Start"

    # Check for "Up" and "Down" Gestures based on thumb position
    thumb_to_wrist_y = thumb_tip.y - wrist.y
    if thumb_to_wrist_y < -threshold:
        print("Detected Gesture: Up (Thumb Above Wrist)")
        return "Up"
    elif thumb_to_wrist_y > threshold:
        print("Detected Gesture: Down (Thumb Below Wrist)")
        return "Down"

    # Default gesture
    print("Detected Gesture: Neutral")
    return "Neutral"


# ---------------------- Gesture Recognition Thread ----------------------
def gesture_recognition_thread(volume, volume_lock, paused, paused_lock, stop_event):
    cap = cv2.VideoCapture(0)
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # Allow only one hand for simplicity
        min_detection_confidence=0.6,  # Slightly increase confidence threshold
        min_tracking_confidence=0.6
    ) as hands:
        print("Gesture Recognition Thread Started.")
        last_pause_time = time.time()
        debounce_time = 0.2  # For pause gesture

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

                # Debugging: Display recognized gesture
                print(f"Recognized Gesture: {gesture}")

                # Continuous volume adjustment for "Up" and "Down"
                if gesture == "Up":
                    with volume_lock:
                        volume[0] = min(volume[0] + 0.01, 1.0)  # Gradual increase
                        pygame.mixer.music.set_volume(volume[0])
                        print(f"Volume increased to {volume[0] * 100:.0f}%")
                elif gesture == "Down":
                    with volume_lock:
                        volume[0] = max(volume[0] - 0.01, 0.0)  # Gradual decrease
                        pygame.mixer.music.set_volume(volume[0])
                        print(f"Volume decreased to {volume[0] * 100:.0f}%")
                elif gesture == "Start" and time.time() - last_pause_time > debounce_time:
                    # Toggle pause/resume
                    with paused_lock:
                        if paused[0]:
                            pygame.mixer.music.unpause()
                            print("Music resumed.")
                            time.sleep(3)
                        else:
                            pygame.mixer.music.pause()
                            print("Music paused.")
                            time.sleep(3)
                        paused[0] = not paused[0]
                    last_pause_time = time.time()

            # Control the frame rate (faster for responsiveness)
            time.sleep(0.05)  # ~20 FPS

    cap.release()
    print("Gesture Recognition Thread Exited.")

# ---------------------- Fetch and Process Song Information ----------------------

async def fetch_song_info(song_id):
    """
    Asynchronously fetches the song's name and picture URL using pycloudmusic.
    """
    musicapi = Music163Api()
    # Get the song by ID
    music = await musicapi.music(song_id)
    # Retrieve the song name and picture URL
    song_name = music.name_str
    pic_url = music.album_data['picUrl']
    return song_name, pic_url

def fetch_image_data(url):
    """
    Fetches the image data from the URL and returns it as bytes.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        return response.content
    except Exception as e:
        sys.exit(f"Failed to fetch image data: {e}")

def preprocess_image(image_data, matrix_width, matrix_height):
    """
    Preprocesses the image to shrink it, display it in the middle, and set the background color to goose yellow.
    Returns a PIL Image object.
    """
    # Open the image from the in-memory bytes
    try:
        image = Image.open(BytesIO(image_data))
    except IOError:
        sys.exit("Cannot open the image data.")

    # Resize the image to be smaller (e.g., 75% of the matrix size)
    shrink_factor = 0.5
    target_width = int(matrix_width * shrink_factor)
    target_height = int(matrix_height * shrink_factor)
    image.thumbnail((target_width, target_height), Image.LANCZOS)

    # Create a blank canvas with goose yellow background
    goose_yellow = (245, 236, 205)  # RGB color for goose yellow
    canvas_image = Image.new("RGB", (matrix_width, matrix_height), goose_yellow)

    # Center the image on the canvas
    image_position = (
        (matrix_width - image.width) // 2,
        (matrix_height - image.height) // 2
    )
    canvas_image.paste(image, image_position)
    return canvas_image

# ---------------------- LED Matrix Display ----------------------

def led_display_thread(matrix, background_image, song_name, font, active_flag, stop_event):
    """
    Thread function to handle LED matrix display.
    Displays the background image and scrolls the song name as text.
    """
    # Initialize variables for scrolling text
    textColor = graphics.Color(4, 4, 3)
    pos = matrix.width  # Starting position of the text
    y_position = matrix.height - 10  # Vertical position of the text

    print("LED Display Thread Started.")

    # Create the frame canvas once outside the loop
    frame_canvas = matrix.CreateFrameCanvas()

    try:
        while not stop_event.is_set():  # Check if the thread is explicitly stopped
            if not active_flag.is_set():  # If paused, wait until active_flag is set
                time.sleep(0.1)
                continue

            # Clear the canvas for the new frame
            frame_canvas.Clear()

            # Set the background image onto the frame canvas
            frame_canvas.SetImage(background_image)

            # Draw the text onto the frame canvas
            try:
                text_length = graphics.DrawText(frame_canvas, font, pos, y_position, textColor, song_name)
            except Exception as e:
                print(f"Error drawing text: {e}")
                text_length = 0

            # Update text position for scrolling
            pos -= 1
            if (pos + text_length < 0):
                pos = frame_canvas.width

            # Swap the frame canvas onto the matrix
            frame_canvas = matrix.SwapOnVSync(frame_canvas)

            # Control the frame rate
            time.sleep(0.05)  # 20 FPS
    except Exception as e:
        print(f"LED Display Thread encountered an error: {e}")

    print("LED Display Thread Exited.")

# ---------------------- Main Execution ----------------------
async def music_scene(song_id):
    # ---------------------- Configuration ----------------------
    try:
        # Get the song's name and picture URL
        song_name, pic_url = await fetch_song_info(song_id)

        print(f"Song Name: {song_name}")
        print(f"Song Picture URL: {pic_url}")

        # Fetch the image data into memory
        image_data = fetch_image_data(pic_url)

        # Configuration for the RGB matrix
        options = RGBMatrixOptions()
        options.rows = 64
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'adafruit-hat'  # Adjust if using a different hardware mapping
        options.brightness = 80                  # Initial brightness (0-100)
        options.gpio_slowdown = 4                 # Adjust GPIO slowdown for stability

        # Initialize the RGB matrix
        try:
            matrix = RGBMatrix(options=options)
        except Exception as e:
            sys.exit(f"Failed to initialize RGB Matrix: {e}")

        # Preprocess the image
        background_image = preprocess_image(image_data, matrix.width, matrix.height)

        # Initialize the font
        font = graphics.Font()
        font_path = "../res/fonts/7x13.bdf"  # Ensure this path is correct
        if not os.path.isfile(font_path):
            sys.exit(f"Font file not found: {font_path}")
        try:
            font.LoadFont(font_path)
        except Exception as e:
            sys.exit(f"Failed to load font: {e}")

        # ---------------------- Music Download and Playback ----------------------

        # Download the music using pycloudmusic
        musicapi = Music163Api()
        music = await musicapi.music(song_id)
        m_quality = music.quality.get('m')
        if m_quality and 'br' in m_quality:
            br = m_quality['br']
        else:
            print("Not available")
            return  # Exit if 'm' quality is not available

        # Download the song
        url = await music._play_url(br)
        print(f"The URL is {url}")
        file_path = await music.play(br, "../res/music/songs")
        print(f"Downloaded File Path: {file_path}")

        # Initialize pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        print("Playing the downloaded music...")

        # Initialize shared variables
        active_flag = threading.Event()
        stop_event = threading.Event()

        volume = [0.5]  # Initial volume
        paused = [False]
        volume_lock = threading.Lock()
        paused_lock = threading.Lock()

        pygame.mixer.music.set_volume(volume[0])

        active_flag.set()  # Set the active_flag initially to allow scrolling

        # Start LED display thread
        led_thread = threading.Thread(target=led_display_thread, args=(
            matrix, background_image, song_name, font, active_flag, stop_event))
        led_thread.start()

        # Start gesture recognition thread
        gesture_thread = threading.Thread(target=gesture_recognition_thread, args=(
            volume, volume_lock, paused, paused_lock, stop_event))
        gesture_thread.start()

        print("Press CTRL-C to stop.")

        try:
            while not stop_event.is_set():
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            print("\nExiting Music Scene.")

        stop_event.set()
        led_thread.join()
        gesture_thread.join()
        pygame.mixer.music.stop()
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred in music_scene: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the asynchronous function and get the song_id
    song_id = asyncio.run(search_music_by_voice(limit=1))
    if song_id:
        asyncio.run(music_scene(song_id))
    else:
        print("Failed to retrieve song ID.")
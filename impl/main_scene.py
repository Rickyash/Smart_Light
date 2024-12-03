# main_scene.py

import cv2
import mediapipe as mp
import time
import sys
import os
import datetime
import threading

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image

from controller import main_scene_gesture_recognition_thread  # Import the gesture recognition thread

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

def led_display_thread(matrix, frame_images, font, brightness_lock, brightness, active_flag, stop_event):
    """
    Thread function to handle LED matrix display.
    Displays GIF frames and scrolls the current time as text.
    """
    num_frames = len(frame_images)
    frame_index = 0

    # Initialize variables for scrolling text
    textColor = graphics.Color(255, 255, 255)
    pos = matrix.width  # Starting position of the text
    y_position = 10     # Vertical position of the text

    print("LED Display Thread Started.")

    # Create a new frame canvas once outside the loop
    frame_canvas = matrix.CreateFrameCanvas()

    while not stop_event.is_set():
        # Clear the canvas for the new frame
        frame_canvas.Clear()

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
        frame_canvas = matrix.SwapOnVSync(frame_canvas)
        # Move to the next frame, looping back to the first frame if necessary
        frame_index = (frame_index + 1) % num_frames
        # Control the frame rate
        time.sleep(0.05)  # 20 FPS

    print("LED Display Thread Exited.")


def main_scene(gif_path):
    # ---------------------- Configuration ----------------------

    # Check for GIF argument
    if not os.path.isfile(gif_path):
        sys.exit(f"File not found: {gif_path}")

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
    frame_images = preprocess_gif(gif_path, matrix.width, matrix.height)

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

    # Start gesture recognition thread from controller.py
    gesture_thread = threading.Thread(target=main_scene_gesture_recognition_thread, args=(
        matrix, brightness_lock, brightness, active_flag, stop_event))
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

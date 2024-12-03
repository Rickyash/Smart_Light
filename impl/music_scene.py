# from pycloudmusic import Music163Api
# import asyncio
# import pygame

# async def main():
#     musicapi = Music163Api()
#     # Get the song with ID 1372554118
#     music = await musicapi.music(1372554118)
#     # Print song information
#     print(music)
#     print("=" * 50)
    
#     # Get lyrics
#     lyrics = await music.lyric()
#     print("Lyrics:")
#     print(lyrics)
#     print("=" * 50)

#     # Get Name
#     Name = music.name_str
#     print("Name:")
#     print(Name)
#     print("=" * 50)
    
#     # Get 'm' quality bitrate
#     m_quality = music.quality.get('m')
#     if m_quality and 'br' in m_quality:
#         br = m_quality['br']
#     else:
#         print("Not available")
#         return  # Exit if 'm' quality is not available
    
#     # Download the song using the 'm' quality bitrate
#     file_path = await music.play(br, "../res/music/songs")
#     print("Downloaded File Path:")
#     print(file_path)

#     # Play the downloaded music using pygame
#     try:
#         print("Playing the downloaded music...")
#         pygame.mixer.init()
#         pygame.mixer.music.load(file_path)
#         pygame.mixer.music.play()
        
#         # Wait until the music finishes playing
#         while pygame.mixer.music.get_busy():
#             await asyncio.sleep(1)
#     except Exception as e:
#         print(f"An error occurred while playing the music: {e}")

# asyncio.run(main())



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
from PIL import Image

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

def led_display_thread(matrix, background_image, song_name, font, brightness_lock, brightness, active_flag, stop_event):
    """
    Thread function to handle LED matrix display.
    Displays the background image and scrolls the song name as text.
    """
    # Initialize variables for scrolling text
    textColor = graphics.Color(4, 4, 3)
    pos = matrix.width  # Starting position of the text
    y_position = matrix.height - 10  # Vertical position of the text

    print("LED Display Thread Started.")

    try:
        while not stop_event.is_set():  # Check if the thread is explicitly stopped
            if not active_flag.is_set():  # If paused, wait until active_flag is set
                time.sleep(0.1)
                continue

            # Create a new frame canvas
            frame_canvas = matrix.CreateFrameCanvas()
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
            matrix.SwapOnVSync(frame_canvas)

            # Control the frame rate
            time.sleep(0.05)  # 20 FPS
    except Exception as e:
        print(f"LED Display Thread encountered an error: {e}")

    print("LED Display Thread Exited.")

# ---------------------- Main Execution ----------------------

def music_scene(song_id):
    # ---------------------- Configuration ----------------------

    # Get the event loop
    loop = asyncio.get_event_loop()
    # Get the song's name and picture URL
    song_name, pic_url = loop.run_until_complete(fetch_song_info(song_id))

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
    options.brightness = 50                   # Initial brightness (0-100)
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
    music = loop.run_until_complete(musicapi.music(song_id))
    m_quality = music.quality.get('m')
    if m_quality and 'br' in m_quality:
        br = m_quality['br']
    else:
        print("Not available")
        return  # Exit if 'm' quality is not available

    # Download the song
    file_path = loop.run_until_complete(music.play(br, "../res/music/songs"))
    print(f"Downloaded File Path: {file_path}")

    # Initialize pygame mixer
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    print("Playing the downloaded music...")

    # ---------------------- LED Matrix Display Threads ----------------------

    # Initialize shared variables
    brightness_lock = threading.Lock()
    brightness = [options.brightness]  # Mutable shared variable
    active_flag = threading.Event()
    stop_event = threading.Event()

    active_flag.set()  # Set the active_flag initially to allow scrolling

    # Start LED display thread
    led_thread = threading.Thread(target=led_display_thread, args=(
        matrix, background_image, song_name, font, brightness_lock, brightness, active_flag, stop_event))
    led_thread.start()

    # ---------------------- Volume and Pause Controls ----------------------
    print("Controls: + (volume up), - (volume down), p (pause/resume), q (quit)")

    paused = False
    volume = 0.5  # Initial volume
    pygame.mixer.music.set_volume(volume)

    try:
        while True:
            user_input = input("Enter control: ").strip().lower()
            if user_input == "+":
                volume = min(1.0, volume + 0.1)  # Increase volume
                pygame.mixer.music.set_volume(volume)
                print(f"Volume increased to {volume * 100:.0f}%")
            elif user_input == "-":
                volume = max(0.0, volume - 0.1)  # Decrease volume
                pygame.mixer.music.set_volume(volume)
                print(f"Volume decreased to {volume * 100:.0f}%")
            elif user_input == "p":
                if paused:
                    pygame.mixer.music.unpause()
                    active_flag.set()  # Resume LED scrolling
                    print("Music resumed.")
                else:
                    pygame.mixer.music.pause()
                    active_flag.clear()  # Pause LED scrolling
                    print("Music paused.")
                paused = not paused
            elif user_input == "q":
                print("Exiting music scene...")
                pygame.mixer.music.stop()
                break
    except KeyboardInterrupt:
        print("\nExiting Music Scene.")

    stop_event.set()  # Signal the thread to stop
    led_thread.join()
    sys.exit(0)

if __name__ == "__main__":
    song_id = 1372554118  
    music_scene(song_id)

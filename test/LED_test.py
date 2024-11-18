#!/usr/bin/env python3
import time
import sys
import os
import datetime

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image

def main():
    # Check for GIF argument
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 gif_viewer_with_time.py <path_to_gif>")
    else:
        image_file = sys.argv[1]
        if not os.path.isfile(image_file):
            sys.exit(f"File not found: {image_file}")

    # Open the GIF file
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

    # Configuration for the matrix
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'  # Adjust if using a different hardware mapping
    options.brightness = 80                   # Adjust brightness as needed (0-100)
    options.gpio_slowdown = 4                 # Adjust GPIO slowdown for stability

    # Initialize the RGB matrix
    try:
        matrix = RGBMatrix(options=options)
    except Exception as e:
        sys.exit(f"Failed to initialize RGB Matrix: {e}")

    # Preprocess the GIF frames into images
    frame_images = []
    print("Preprocessing GIF frames...")
    for frame_index in range(num_frames):
        try:
            gif.seek(frame_index)
            # Copy the frame to avoid modifying the original GIF
            frame = gif.copy()
            # Resize the frame to fit the matrix while maintaining aspect ratio
            frame.thumbnail((matrix.width, matrix.height), Image.LANCZOS)
            # Create a blank canvas and paste the frame onto it centered
            canvas_image = Image.new("RGB", (matrix.width, matrix.height), (0, 0, 0))
            frame_position = (
                (matrix.width - frame.width) // 2,
                (matrix.height - frame.height) // 2
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
    print("Preprocessing completed. Starting GIF display...")

    # Initialize variables for scrolling text
    font = graphics.Font()
    # Adjust the path to your font file
    font.LoadFont("../res/fonts/clR6x12.bdf")
    textColor = graphics.Color(255, 255, 255)
    pos = matrix.width  # Starting position of the text
    y_position = 10  # Vertical position of the text
    cur_frame = 0

    print("Press CTRL-C to stop.")
    try:
        while True:
            # Create a new frame canvas
            frame_canvas = matrix.CreateFrameCanvas()
            # Get the current frame image
            frame_image = frame_images[cur_frame]
            # Set the image onto the frame canvas
            frame_canvas.SetImage(frame_image)
            # Get the current time as text
            current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
            # Draw the text onto the frame canvas
            text_length = graphics.DrawText(frame_canvas, font, pos, y_position, textColor, current_time_str)
            # Update text position for scrolling
            pos -= 1
            if (pos + text_length < 0):
                pos = frame_canvas.width
            # Swap the frame canvas onto the matrix
            frame_canvas = matrix.SwapOnVSync(frame_canvas)
            # Move to the next frame, looping back to the first frame if necessary
            if cur_frame == num_frames - 1:
                cur_frame = 0
            else:
                cur_frame += 1
            # Adjust sleep time as necessary to control frame rate
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nGIF display stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred during display: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

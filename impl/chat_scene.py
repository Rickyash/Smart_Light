# working!!!!!!!!!!!
import openai
import speech_recognition as sr
import os
import sys
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import time
import threading

# Suppress warnings
sys.stderr = open(os.devnull, 'w')
os.environ["PYTHONWARNINGS"] = "ignore"

# Set OpenAI API key 
# openai.api_key = "API-KEY"

# LED Matrix configuration
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.brightness = 75 
options.gpio_slowdown = 4

matrix = RGBMatrix(options=options)

def display_text_with_fade_and_move(text, fade_out=False, delay=0.05):
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_size = 8
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        sys.exit(1)
    dummy_image = Image.new("RGB", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_image)
    text_width, text_height = dummy_draw.textsize(text, font=font)
    image_width = text_width + 64
    image = Image.new("RGB", (image_width, 64), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    y_position = (64 - text_height) // 2
    draw.text((64, y_position), text, font=font, fill=(255, 255, 255))
    for x in range(0, image_width - 64 + 1):
        frame = image.crop((x, 0, x + 64, 64))
        matrix.SetImage(frame)
        time.sleep(delay)
    if fade_out:
        for brightness in range(255, -1, -16):
            faded_image = image.point(lambda p: p * (brightness / 255))
            frame = faded_image.crop((image_width - 64, 0, image_width, 64))
            matrix.SetImage(frame.convert("RGB"))
            time.sleep(delay)
    matrix.Clear()

def listen_for_wake_word(wake_word="hello there"):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print(f"Say '{wake_word}' to activate the assistant...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            spoken_text = recognizer.recognize_google(audio).lower()
            print(f"Heard: {spoken_text}")
            if wake_word in spoken_text:
                return True
        except sr.WaitTimeoutError:
            print("Listening timed out while waiting for the wake word.")
        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
    return False

def listen_for_query():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Listening for your query...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            query = recognizer.recognize_google(audio)
            print(f"You said: {query}")
            return query
        except sr.WaitTimeoutError:
            print("Listening timed out while waiting for the query.")
        except sr.UnknownValueError:
            print("Could not understand the query.")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")   
    return None

def get_openai_response(input_text):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Provide answers in less than 20 words."},
                {"role": "user", "content": input_text}
            ]
        )
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print(f"An error occurred while communicating with OpenAI: {e}")
        return None

def display_gif(gif_path, stop_event, delay=0.1):
    """
    Displays a GIF on the LED matrix continuously until stop_event is set.
    """
    try:
        gif = Image.open(gif_path)
    except IOError:
        print(f"Cannot open GIF file")
        return

    try:
        num_frames = gif.n_frames
    except AttributeError:
        print("Provided image is not a GIF.")
        return

    # Preprocess the gif frames into canvases to improve playback performance
    canvases = []
    print("Preprocessing gif, this may take a moment depending on the size of the gif...")
    for frame_index in range(num_frames):
        try:
            gif.seek(frame_index)
            frame = gif.copy()
            frame = frame.convert("RGB")
            frame = frame.resize((64, 64), Image.ANTIALIAS)
            canvases.append(frame)
        except EOFError:
            break  # End of sequence

    gif.close()
    print("Completed Preprocessing, displaying gif")

    frame_index = 0
    while not stop_event.is_set():
        frame = canvases[frame_index]
        matrix.SetImage(frame)
        time.sleep(delay)
        frame_index = (frame_index + 1) % num_frames

    matrix.Clear()

def display_static_text(text, background_color=(255, 255, 255), text_color=(0, 0, 0)):
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_size = 10

    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print("Font file not found. Please install the specified font.")
        sys.exit(1)

    image = Image.new("RGB", (64, 64), background_color)
    draw = ImageDraw.Draw(image)

    # Calculate text size to center it
    text_width, text_height = draw.textsize(text, font=font)
    x = (64 - text_width) // 2
    y = (64 - text_height) // 2

    # Draw the text onto the image
    draw.text((x, y), text, font=font, fill=text_color)

    # Display the image on the LED matrix
    matrix.SetImage(image)

def chat_scene():
    while True:
        display_stop_event = threading.Event()
        default_display_thread = threading.Thread(target=display_static_text, args=("CHAT",))
        default_display_thread.start()
        wake_detected = listen_for_wake_word()
        if wake_detected:
            display_stop_event.set()
            default_display_thread.join()
            stop_event = threading.Event()
            display_thread = threading.Thread(target=display_gif, args=("../res/gifs/loop.gif", stop_event,))
            display_thread.start()
            query = listen_for_query()
            stop_event.set()
            display_thread.join()
            if query:
                answer = get_openai_response(query)
                if answer:
                    display_text_with_fade_and_move(answer, fade_out=True)
        else:
            display_stop_event.set()
            default_display_thread.join()

def test():
    display_text_with_fade_and_move("okay!wwwwwwwwwwwwwwwwwwwwww", fade_out=True) 

if __name__ == "__main__":
    try:
        chat_scene()
    except KeyboardInterrupt:
        print("\nAssistant terminated by user.")

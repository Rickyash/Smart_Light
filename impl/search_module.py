# search_module.py
from pycloudmusic import Music163Api
import speech_recognition as sr
import asyncio
import os
import sys


async def main():
    # Redirect stderr to suppress ALSA warnings
    sys.stderr = open(os.devnull, 'w')
    # Initialize the music API
    musicapi = Music163Api()

    # Initialize the recognizer
    recognizer = sr.Recognizer()

    # Use the microphone for voice input
    with sr.Microphone() as source:
        print("Say 'search music' to start...")

        # Adjust for ambient noise and capture the command
        recognizer.adjust_for_ambient_noise(source)
        try:
            command = recognizer.listen(source)
            command_text = recognizer.recognize_google(command).lower()
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand the command.")
            return
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return

    # Check if the command is "search music"
    if "search music" in command_text:
        print("You can now say the song title...")
        with sr.Microphone() as source:
            try:
                recognizer.adjust_for_ambient_noise(source)
                print("Listening for the song title...")
                song_title_audio = recognizer.listen(source)
                song_title = recognizer.recognize_google(song_title_audio)
                print(f"Searching for: {song_title}")
            except sr.UnknownValueError:
                print("Sorry, I couldn't understand the song title.")
                return
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                return

        # Use the recognized song title as the search key
        key = song_title
        page = 0
        limit = 1

        # Call the search_music function
        result_count, music_generator = await musicapi.search_music(key, page, limit)

        # Print the total result count
        print(f"Total Results: {result_count}")
        print("=" * 50)

        # Iterate through the generator to display results
        print("Search results:")
        for music in music_generator:
            # Assuming `music` has attributes like `title` and `artist`
            print(f"Music: {music}")
    else:
        print("Command not recognized. Please say 'search music' to begin.")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())

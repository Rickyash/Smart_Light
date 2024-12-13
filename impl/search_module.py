# search_module.py
from pycloudmusic import Music163Api
import speech_recognition as sr
import asyncio
import os
import sys

async def search_music_by_voice(limit=1):
    """
    Listens for a voice command to search for music and returns the music ID.

    Parameters:
        limit (int): The number of search results to retrieve. Defaults to 1.

    Returns:
        str: The ID of the found music. Returns None if not found or on failure.
    """
    # Redirect stderr to suppress ALSA warnings
    sys.stderr = open(os.devnull, 'w')

    # Initialize the music API
    musicapi = Music163Api()

    # Initialize the recognizer
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("Say 'search music' to start...")
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source)
            # Listen for the initial command
            command = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            command_text = recognizer.recognize_google(command).lower()
            print(f"Command received: {command_text}")
    except sr.WaitTimeoutError:
        print("Listening timed out while waiting for the command.")
        return None
    except sr.UnknownValueError:
        print("Sorry, I couldn't understand the command.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from the speech recognition service; {e}")
        return None

    # Check if the command is "search music"
    if "search music" in command_text:
        try:
            with sr.Microphone() as source:
                print("You can now say the song title...")
                recognizer.adjust_for_ambient_noise(source)
                print("Listening for the song title...")
                song_title_audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                song_title = recognizer.recognize_google(song_title_audio)
                print(f"Searching for: {song_title}")
        except sr.WaitTimeoutError:
            print("Listening timed out while waiting for the song title.")
            return None
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand the song title.")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from the speech recognition service; {e}")
            return None

        # Use the recognized song title as the search key
        key = song_title
        page = 0
        limit = limit

        try:
            # Call the search_music function
            result_count, music_generator = await musicapi.search_music(key, page, limit)

            # Check if any results were found
            if result_count == 0:
                print("No music found for the given title.")
                return None

            # Iterate through the generator to get the first music item
            for music in music_generator:
                print(f"Found Music: {music.name} by {music.artist} (ID: {music.id})")
                return music.id

        except Exception as e:
            print(f"An error occurred while searching for music: {e}")
            return None
    else:
        print("Command not recognized. Please say 'search music' to begin.")
        return None

# Example usage
if __name__ == "__main__":
    music_id = asyncio.run(search_music_by_voice())
    if music_id:
        print(f"Retrieved Music ID: {music_id}")
    else:
        print("Failed to retrieve Music ID.")

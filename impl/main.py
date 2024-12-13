# main.py
import sys

def main():
    print("Please select a scene to run:")
    print("1 - Main Scene")
    print("2 - Music Scene")
    print("3 - Chat Scene")
    choice = input("Enter your choice (1/2/3): ")

    if choice == "1":
        from main_scene import main_scene
        gif_path = "../res/gifs/city.gif"
        main_scene(gif_path)
    elif choice == "2":
        from music_scene import music_scene
        song_id = 1372554118
        music_scene(song_id)
    elif choice == "3":
        from chat_scene import chat_scene
        chat_scene()
        
    else:
        print("Invalid choice. Please run the program again and select 1, 2, or 3.")

if __name__ == "__main__":
    main()

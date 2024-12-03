from pycloudmusic import Music163Api
import asyncio
import pygame

async def main():
    musicapi = Music163Api()
    # Get the song with ID 1372554118
    # User = await musicapi.user(295583354)
    # music = await musicapi.music(1372554118)
    # # Print song information
    # print(music)
    # print("=" * 50)
    
    # Get lyrics
    # lyrics = await music.lyric()
    # print("Lyrics:")
    # print(lyrics)
    # print("=" * 50)

    # Get Name
    # Name = music.name_str
    # print("Name:")
    # print(Name)
    # print("=" * 50)
    
    # Get 'm' quality bitrate
    # m_quality = music.quality.get('m')
    # if m_quality and 'br' in m_quality:
    #     br = m_quality['br']
    # else:
    #     print("Not available")
    #     return  # Exit if 'm' quality is not available
    
    # Download the song using the 'm' quality bitrate
    # file_path = await music.play(br, "../res/music/songs")
    # print("Downloaded File Path:")
    # print(file_path)

    # Play the downloaded music using pygame
    # try:
    #     print("Playing the downloaded music...")
    #     pygame.mixer.init()
    #     pygame.mixer.music.load(file_path)
    #     pygame.mixer.music.play()
        
    #     # Wait until the music finishes playing
    #     while pygame.mixer.music.get_busy():
    #         await asyncio.sleep(1)
    # except Exception as e:
    #     print(f"An error occurred while playing the music: {e}")

    # user function testing
    # User_like = await User.like_music()
    # print("User_like:")
    # print(User_like.music_list[10])
    # print("=" * 50)

    key = "One Last Kiss"
    page = 0
    limit = 1
    # Call the function
    result_count, music_generator = await musicapi.search_music(key, page, limit)

    # Print the total result count
    print(f"Total Results: {result_count}")
    print("=" * 50)

    # Iterate through the generator to display results
    print("Search results:")
    for music in music_generator:
        # Assuming `music` has attributes like `title` and `artist`
        print(f"Music: {music.id}")

asyncio.run(main())

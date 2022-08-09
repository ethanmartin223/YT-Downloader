from yt_downloader import *
import requests
import io
import warnings

MAIN_MENU_SCREEN = 'YouTube Video Downloader\nA Project By Ethan Martin, with help from Gabe Rottet'
os.system("color")

while True:
    print('\033c', end='')
    print(MAIN_MENU_SCREEN)

    link = input('\nEnter Youtube link: \033[38;2;255;255;0m')

    yt_vid = YouTubeVideo(link)

    print('\033c', end='')

    infojson = yt_vid.video_metadata["videoDetails"]
    seconds = str(int(infojson['lengthSeconds']) % 60)
    print(f"\033[38;2;0;255;0m{infojson['title']}\nDuration: {int(infojson['lengthSeconds']) // 60}:" \
          f"{'0' + seconds if len(seconds) == 1 else seconds}\nAuthor: {infojson['author']}\033[0m"
          )

    print('\033[0m\nPick a resolution to download video:')
    for i, resolution in enumerate(yt_vid.resolution_data.keys()):
        print(f'\t[\033[38;2;0;255;0m{i}\033[0m] {resolution}')

    flg = True
    while flg:
        try:
            quality = int(input('\nOption # : \033[38;2;255;255;0m'))
            if quality > i or quality < 0:
                raise ValueError
            flg = False
        except ValueError:
            print('\033[38;2;255;0;0mEnter a valid number corresponding to the quality listed.\033[0m')
    quality = list(yt_vid.resolution_data.keys())[quality]

    print('\033c', end='')
    print('Choose output filetype: ')
    for i, preset in enumerate(yt_vid.avalible_output_formats):
        print(f'\t[\033[38;2;0;255;0m{i}\033[0m] {preset}')

    flg = True
    while flg:
        try:
            choosen_preset = int(input('\nOption # : \033[38;2;255;255;0m'))
            if choosen_preset > i or choosen_preset < 0:
                raise ValueError
            flg = False
        except ValueError:
            print('\033[38;2;255;0;0mEnter a valid number corresponding to the quality listed.\033[0m')

    yt_vid.output_filetype = choosen_preset

    print('\033c', end='')
    print('\033[0mStarting Download...')

    yt_vid.download_video(quality)
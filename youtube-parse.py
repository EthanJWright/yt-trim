"""Download and trim youtube audio"""
import re
from os import walk
from pathlib import Path
import argparse
import youtube_dl

from pydub import AudioSegment


YOUTUBE_OUT = "./outputs/"
TRIM_OUT = "./sounds/"


class MyLogger:
    """Print youtube DL logs"""

    def __init__(self):
        self.download_repos = []

    @staticmethod
    def __get_between(msg):
        print(f"Parsing: {msg}")
        result = re.search("./outputs/(.*)/", msg)
        if result is None:
            return None
        return result.group(1)

    def debug(self, msg):
        """print debug messages"""
        if "download" in msg:
            if "Destination" in msg:
                directory = self.__get_between(msg)
                if directory is not None and directory not in self.download_repos:
                    self.download_repos.append(directory)

        print(f"Debug: {msg}")

    @staticmethod
    def warning(msg):
        """print warning messages"""
        print(f"Warning {msg}")

    @staticmethod
    def error(message):
        """print error messages"""
        print(f"Error: {message}")


def my_hook(data):
    """Handle youtubedl finishing download"""
    if data["status"] == "finished":
        print("Done downloading, now converting...")


def min_to_mili(time):
    """convert minutes to miliseconds"""
    return time * 60 * 1000


def trim_file(file, start=0, end=15):
    """trim the length of an audiofile"""
    start_time = min_to_mili(start)
    end_time = min_to_mili(end)
    song = AudioSegment.from_mp3(file)
    return song[start_time:end_time]


def write_new_file(extracted_song, new_file_name):
    """write a trimmed file to a new file"""
    extracted_song.export(new_file_name, format="mp3")


def out_path(repo, filename):
    return f"{YOUTUBE_OUT}{repo}/{filename}"


def trim_dir(repo):
    return f"{TRIM_OUT}{repo}/"


def trim_path(repo, filename):
    return f"{trim_dir(repo)}{filename}"


def mkdir_pv(ensure_dir):
    Path(ensure_dir).mkdir(parents=True, exist_ok=True)


def trim_output(repo, duration=None):
    if duration is None:
        duration = 1

    print(f"Trimming files to duration of {duration} minutes")
    path = f"{YOUTUBE_OUT}{repo}"
    _, _, filenames = next(walk(path))
    for filename in filenames:
        if "mp3" in filename:
            audio = trim_file(out_path(repo, filename), end=duration)
            mkdir_pv(trim_dir(repo))
            write_new_file(audio, trim_path(repo, filename))
            print(f"Trimmed -- [{filename}]")


def download_playlist(id=None, output_dir=""):
    yt_log = MyLogger()
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "logger": yt_log,
        "progress_hooks": [my_hook],
        "outtmpl": f"{output_dir}%(playlist_title)s/%(title)s-%(id)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([id])
    return yt_log.download_repos


def main():
    """entrypoint"""

    parser = argparse.ArgumentParser(
        prog="Download youtube videos as trimmed MP3s", usage="%(prog)s [--playlist]"
    )

    parser.add_argument("--playlist")
    parser.add_argument("--duration", type=int)
    args = parser.parse_args()

    repos = download_playlist(id=args.playlist, output_dir=YOUTUBE_OUT)

    for repo in repos:
        trim_output(repo, args.duration)


if __name__ == "__main__":
    main()

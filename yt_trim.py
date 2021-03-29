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

    @staticmethod
    def warning(msg):
        """print warning messages"""
        print(f"Warning {msg}")

    @staticmethod
    def error(message):
        """print error messages"""
        print(f"Error: {message}")


class YouTube:
    @staticmethod
    def dl_hook(data):
        """Handle youtubedl finishing download"""
        if "_percent_str" in data:
            percent = data["_percent_str"]
            percent = percent.replace("%", "")
            print(f"{percent}%...")

        if data["status"] == "finished":
            print(f"Downloaded {data['filename']}")

    @staticmethod
    def __min_to_mili(time):
        """convert minutes to miliseconds"""
        return time * 60 * 1000

    def __trim_file(self, file, start=0, end=0):
        """trim the length of an audiofile"""
        start_time = self.__min_to_mili(start)
        end_time = self.__min_to_mili(end)
        song = AudioSegment.from_mp3(file)
        if end == 0:
            return song
        return song[start_time:end_time]

    @staticmethod
    def __write_new_file(extracted_song, new_file_name):
        """write a trimmed file to a new file"""
        extracted_song.export(new_file_name, format="mp3")

    @staticmethod
    def __out_path(out=YOUTUBE_OUT, repo="", filename=""):
        """full path for file being downloaded"""
        return f"{out}{repo}/{filename}"

    @staticmethod
    def __trim_dir(repo):
        """directory that trimmed files are saved in"""
        return f"{TRIM_OUT}{repo}/"

    def __trim_path(self, repo, filename):
        """full path for file being trimmed to be saved"""
        return f"{self.__trim_dir(repo)}{filename}"

    @staticmethod
    def __mkdir_pv(ensure_dir):
        """make a directory if it doesn't exist"""
        Path(ensure_dir).mkdir(parents=True, exist_ok=True)

    def trim_output(self, out_dir, repo, duration=None):
        """trim all files in a repo"""
        if duration is None:
            duration = 1

        if duration != 1:
            print(f"Trimming files to duration of {duration} minutes")
        else:
            print("Copying files to destination...")
        path = f"{out_dir}{repo}"
        _, _, filenames = next(walk(path))
        for filename in filenames:
            if "mp3" in filename:
                audio = self.__trim_file(
                    self.__out_path(out=out_dir, repo=repo, filename=filename),
                    end=duration,
                )
                self.__mkdir_pv(self.__trim_dir(repo))
                self.__write_new_file(audio, self.__trim_path(repo, filename))
                print(f"Processed -- [{filename}]")

    def download_playlist(self, playlist_id=None, output_dir=""):
        """download a youtube playlist"""
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
            "progress_hooks": [self.dl_hook],
            "outtmpl": f"{output_dir}%(playlist_title)s/%(title)s-%(playlist_id)s.%(ext)s",
            "restrictfilenames": True,
            "noplaylist": True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([playlist_id])
        return yt_log.download_repos


def main():
    """entrypoint"""

    parser = argparse.ArgumentParser(
        prog="Download youtube videos as trimmed MP3s", usage="%(prog)s [--playlist]"
    )

    parser.add_argument("--playlist", help="playlist_id of the playlist to download")
    parser.add_argument(
        "--duration", type=int, help="Duration of output file, in minutes"
    )
    args = parser.parse_args()

    youtube = YouTube()
    repos = youtube.download_playlist(playlist_id=args.playlist, output_dir=YOUTUBE_OUT)

    for repo in repos:
        youtube.trim_output(YOUTUBE_OUT, repo, args.duration)


if __name__ == "__main__":
    main()

"""Download and trim youtube audio"""
from urllib.error import HTTPError
import sys
import re
import os
import argparse
import shutil
import youtube_dl

from convert import Convert
from file_observer import FileObserver


YOUTUBE_OUT = "./download_temporary_data/"
TRIM_OUT = "./files/"


class YoutubeDLLogger:
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
    """manage API for downloading and processing files"""

    def __init__(self):
        self.__filename_map_hooks = [self.__remove_after_dash]
        self.__done_hooks = [self.__delete_process_dir]
        # self.__done_hooks = []
        self.__duration = 0
        self.__converter = Convert(output_dir="./files/")
        self.__temporary_dir = "./download_temporary_data/"
        self.__file_observer = FileObserver(self.__temporary_dir, patterns=["*.mp3"])
        self.__file_observer.load_handler(
            "on_modified_done", self.on_file_done_modified
        )

    def set_processed_dir(self, directory):
        """set what directory processed files should be placed in"""
        self.__converter.set_output_dir(directory)

    def set_temporary_dir(self, directory):
        """set output dir"""
        self.__temporary_dir = directory

    def convert_downloads(self):
        """configure youtube to wait for files to be downloaded, then run converters on them"""
        self.__file_observer.start()

    @staticmethod
    def __delete_process_dir(output_dir=""):
        """delete the directory used to store youtube downloads"""
        shutil.rmtree(output_dir)

    def add_filename_map(self, method):
        """add a method to process file names"""
        self.__filename_map_hooks.append(method)

    @staticmethod
    def __prune(path):
        print(f"Pruning MP3 and MP4 from [{path}]")
        for root, dirs, files in os.walk(path):
            del dirs
            for current_file in files:
                exts = (".mp3", ".mp4")
                if current_file.lower().endswith(exts):
                    os.remove(os.path.join(root, current_file))

    @staticmethod
    def __remove_after_dash(file):
        dash_split = file.split("-")
        return f"{dash_split[0]}.mp3"

    def __temporary_data_path(self, repo, filename):
        """full path for file being downloaded"""
        return f"{self.__temporary_dir}{repo}{filename}"

    @staticmethod
    def __extract_ytdl_fileprops(filename):
        props = filename.split("/")
        file = props[3].split(".")[0]
        # out_dir, repo, filename
        return (f"./{props[1]}/", f"{props[2]}/", f"{file}.mp3")

    def on_file_done_modified(self, event):
        """bind action to when a file is done being modified (video fully downloaded)"""
        full_file = event.src_path
        (_, repo, filename) = self.__extract_ytdl_fileprops(full_file)
        audio = self.__converter.trim(full_file, self.__duration)
        filename = self.__converter.process_filename(filename)
        self.__converter.write(repo, audio, filename)

    @staticmethod
    def dl_hook(data):
        """Handle youtubedl finishing download"""
        if "_percent_str" in data:
            percent = data["_percent_str"]
            percent = percent.replace("%", "")
            print(f"{percent}%...")

        if data["status"] == "finished":
            print("Finished download.")

    def download(self, source_id=None, output_dir="", duration=0):
        """download youtube audio from a source"""
        if duration is not None:
            self.__duration = duration
        yt_log = YoutubeDLLogger()
        self.set_temporary_dir(output_dir)
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
            "outtmpl": f"{self.__temporary_dir}%(playlist_title)s/%(title)s-%(source_id)s.%(ext)s",
            "restrictfilenames": True,
            "noplaylist": True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source_id])
        return yt_log.download_repos

    def done(self):
        """youtube methods complete, clean up"""
        if self.__file_observer.is_watching():
            self.__file_observer.stop()
        for method in self.__done_hooks:
            method(self.__temporary_dir)


def main():
    """entrypoint"""

    parser = argparse.ArgumentParser(
        prog="Download youtube videos as trimmed MP3s", usage="%(prog)s [--playlist]"
    )

    parser.add_argument(
        "--source", help="Youtube ID of source, video ID or playlist ID"
    )
    parser.add_argument(
        "--duration", type=int, help="Duration of output file, in minutes"
    )
    args = parser.parse_args()

    youtube = YouTube()
    youtube.set_temporary_dir(YOUTUBE_OUT)
    youtube.convert_downloads()

    try:
        youtube.download(
            source_id=args.source, output_dir=YOUTUBE_OUT, duration=args.duration
        )
    except HTTPError:
        print("Cant download video, exiting...")
        sys.exit()

    youtube.done()


if __name__ == "__main__":
    main()

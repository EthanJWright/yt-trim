"""Download and trim youtube audio"""
from urllib.error import HTTPError
import sys
import re
import os
from pathlib import Path
import argparse
import shutil
import youtube_dl


from pydub import AudioSegment


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
        self.__output_dir = ""
        self.__duration = 0
        self.__out_dir = ""

    def set_out(self, directory):
        """set output dir"""
        self.__out_dir = directory

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

    def __trim_downloaded_file(self, filename, out_dir, repo, duration):
        if "mp3" in filename:
            audio = self.__trim_file(
                self.__out_path(out=out_dir, repo=repo, filename=filename),
                end=duration,
            )
            self.__mkdir_pv(self.__trim_dir(repo))
            # change output filename based on loaded methods
            filename = self.__process_filename(filename)
            self.__write_new_file(audio, self.__trim_path(repo, filename))
            print(f"Processed -- [{filename}]")

    @staticmethod
    def __extract_ytdl_fileprops(filename):
        props = filename.split("/")
        file = props[3].split(".")[0]
        # out_dir, repo, filename
        return (f"./{props[1]}/", f"{props[2]}/", f"{file}.mp3")

    def dl_hook(self, data):
        """Handle youtubedl finishing download"""
        if "_percent_str" in data:
            percent = data["_percent_str"]
            percent = percent.replace("%", "")
            print(f"{percent}%...")

        if data["status"] == "finished":
            (out_dir, repo, _) = self.__extract_ytdl_fileprops(data["filename"])
            self.trim_output(out_dir, repo, self.__duration)
            self.__prune(f"{out_dir}{repo}")

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
    def __write_new_file(extracted_song, new_file):
        """write a trimmed file to a new file"""
        print(f"Writing file to: {new_file}")
        extracted_song.export(new_file, format="mp3")

    @staticmethod
    def __path(out, repo):
        return f"{out}{repo}"

    @staticmethod
    def __no_repo_path(out):
        return out

    def __out_path(self, out=YOUTUBE_OUT, repo="", filename=""):
        """full path for file being downloaded"""
        return f"{self.__path(out, repo)}{filename}"

    def __trim_dir(self, repo):
        """directory that trimmed files are saved in"""
        if repo == "NA/":
            return self.__no_repo_path(TRIM_OUT)
        return self.__path(TRIM_OUT, repo)

    def __trim_path(self, repo, filename):
        """full path for file being trimmed to be saved"""
        return f"{self.__trim_dir(repo)}{filename}"

    @staticmethod
    def __mkdir_pv(ensure_dir):
        """make a directory if it doesn't exist"""
        Path(ensure_dir).mkdir(parents=True, exist_ok=True)

    def __process_filename(self, filename):
        for method in self.__filename_map_hooks:
            filename = method(filename)
        return filename

    def trim_output(self, out_dir, repo, duration):
        """trim all files in a repo"""
        if duration is None:
            duration = 1

        if duration != 1:
            print(f"Trimming files to duration of {duration} minutes")
        else:
            print("Copying files to destination...")
        path = f"{out_dir}{repo}"
        _, _, filenames = next(os.walk(path))
        for filename in filenames:
            self.__trim_downloaded_file(filename, out_dir, repo, duration)

    def download(self, source_id=None, output_dir="", duration=0):
        """download youtube audio from a source"""
        if duration is not None:
            self.__duration = duration
        yt_log = YoutubeDLLogger()
        self.__output_dir = output_dir
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
            "outtmpl": f"{output_dir}%(playlist_title)s/%(title)s-%(source_id)s.%(ext)s",
            "restrictfilenames": True,
            "noplaylist": True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source_id])
        return yt_log.download_repos

    def done(self):
        """youtube methods complete, clean up"""
        for method in self.__done_hooks:
            method(self.__output_dir)


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
    youtube.set_out(YOUTUBE_OUT)

    try:
        repos = youtube.download(
            source_id=args.source, output_dir=YOUTUBE_OUT, duration=args.duration
        )
    except HTTPError:
        print("Cant download video, exiting...")
        sys.exit()

    for repo in repos:
        youtube.trim_output(YOUTUBE_OUT, repo, args.duration)

    youtube.done()


if __name__ == "__main__":
    main()

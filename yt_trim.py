"""Download and trim youtube audio"""
from urllib.error import HTTPError
import sys
import time
import re
import os
from pathlib import Path
import argparse
import shutil
import youtube_dl
from pydub import AudioSegment
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import threading

from convert import Convert


YOUTUBE_OUT = "./download_temporary_data/"
TRIM_OUT = "./files/"


class ModifiedDoneThread(threading.Thread):
    """Track when a file hasnt been modified for a second"""

    def __init__(self, handlers, modified_timers):
        threading.Thread.__init__(self)
        # dict of tyep { "last_modified": time, "event": event }
        self.__modified_timers = modified_timers
        self.__handlers = handlers

    def run(self):
        while len(self.__modified_timers) > 0:
            time.sleep(1)
            now = time.time()
            remove_timers = []
            for (key, value) in self.__modified_timers.items():
                last_modified = value["last_modified"]
                if now - last_modified > 1:
                    print(f"calling ({len(self.__handlers)}) handlers")
                    for handler in self.__handlers:
                        handler(value["event"])
                    remove_timers.append(key)

            for timer in remove_timers:
                self.__modified_timers.pop(timer, None)


class FileObserver:
    def __init__(self, directory="./", patterns=["*.mp3"], case_sensitive=True):
        self.__on_handlers = {"on_modified_done": []}
        self.__directory = directory
        self.__handler = PatternMatchingEventHandler(patterns, "", True, case_sensitive)
        self.__recursive = True
        self.__observer = Observer()
        self.__watching = False
        self.__modified_timers = {}
        self.__modified_thread = None

    @staticmethod
    def __mkdir_pv(ensure_dir):
        """make a directory if it doesn't exist"""
        Path(ensure_dir).mkdir(parents=True, exist_ok=True)

    def load_handler(self, event, handler):
        """load a handler for when an """
        if event in self.__on_handlers:
            self.__on_handlers[event].append(handler)
        else:
            self.__on_handlers[event] = [handler]

    def __on_created(self, event):
        print(f"in on created!")
        if "on_created" in self.__on_handlers:
            for handler in self.__on_handlers["on_created"]:
                handler(event)

    def __on_modified(self, event):
        start_thread = False
        if len(self.__modified_timers) == 0:
            self.__modified_thread = ModifiedDoneThread(
                self.__on_handlers["on_modified_done"],
                self.__modified_timers,
            )
            start_thread = True

        if "on_modified" in self.__on_handlers:
            for handler in self.__on_handlers["on_modified"]:
                handler(event)
        self.__modified_timers[event.src_path] = {
            "event": event,
            "last_modified": time.time(),
        }
        if start_thread:
            self.__modified_thread.start()

    def is_watching(self):
        """check if observer is currently watching for updates"""
        return self.__watching

    def start(self):
        """Start observing the file system"""
        self.__mkdir_pv(self.__directory)
        self.__watching = True
        self.__handler.on_created = self.__on_created
        self.__handler.on_modified = self.__on_modified
        self.__observer.schedule(self.__handler, self.__directory, self.__recursive)
        self.__observer.start()

    def stop(self):
        """Stop observing the file system"""
        print(f"Stop called")
        self.__modified_thread.join()
        self.__observer.stop()
        self.__observer.join()
        self.__watching = False


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
        # self.__done_hooks = [self.__delete_process_dir]
        self.__done_hooks = []
        self.__duration = 0
        self.__converter = Convert()
        self.__temporary_dir = "./download_temporary_data/"
        self.__file_observer = FileObserver(self.__temporary_dir, patterns=["*.mp3"])
        self.__file_observer.load_handler(
            "on_modified_done", self.on_file_done_modified
        )

    def set_temporary_dir(self, directory):
        """set output dir"""
        self.__temporary_dir = directory

    def convert_downloads(self):
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

    def __trim_downloaded_file(self, filename, out_dir, repo, duration):
        print(f"Trimming file: {filename}")
        if "mp3" in filename:
            file_path = self.__temporary_data_path(repo, filename)
            audio = self.__converter.trim(file_path, duration)
            filename = self.__converter.process_filename(filename)
            # change output filename based on loaded methods
            self.__converter.write(repo, audio, filename)
            print(f"Processed -- [{filename}]")

    @staticmethod
    def __extract_ytdl_fileprops(filename):
        props = filename.split("/")
        file = props[3].split(".")[0]
        # out_dir, repo, filename
        return (f"./{props[1]}/", f"{props[2]}/", f"{file}.mp3")

    def on_file_done_modified(self, event):
        print(f"IN FILE DONE MODIFIED {event.src_path}")
        full_file = event.src_path
        (out_dir, repo, filename) = self.__extract_ytdl_fileprops(full_file)
        audio = self.__converter.trim(full_file, self.__duration)
        filename = self.__converter.process_filename(filename)
        self.__converter.write(repo, audio, filename)

    def dl_hook(self, data):
        """Handle youtubedl finishing download"""
        if "_percent_str" in data:
            percent = data["_percent_str"]
            percent = percent.replace("%", "")
            print(f"{percent}%...")

        if data["status"] == "finished":
            print(f"Finished download.")
            # (out_dir, repo, filename) = self.__extract_ytdl_fileprops(full_file)
            # audio = self.__converter.trim(full_file, self.__duration)
            # filename = self.__converter.process_filename(filename)
            # self.__converter.write(repo, audio, filename)
            # self.__prune(f"{out_dir}{repo}")

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
        if extracted_song is None:
            print(f"Couldnt load file, failed to write {new_file}")
            return
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
            duration = 0

        if duration != 0:
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
        for method in self.__done_hooks:
            method(self.__temporary_dir)
        if self.__file_observer.is_watching():
            self.__file_observer.stop()


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

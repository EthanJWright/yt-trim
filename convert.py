"""Convert and process files"""
from pathlib import Path
from pydub import AudioSegment


class Convert:
    """trim and rename files"""

    def __init__(self, output_dir=""):
        self.__output_dir = output_dir
        self.__filename_map_hooks = [
            self.__remove_after_dash,
            self.__remove_duplicate_mp3,
        ]

    @staticmethod
    def __remove_duplicate_mp3(file):
        # TODO: debug sometimes double mp3
        return file
        # return file.replace("mp3", "")

    @staticmethod
    def __remove_after_dash(file):
        dash_split = file.split("-")
        return f"{dash_split[0]}.mp3"

    def set_output_dir(self, directory):
        """load the directory to write files to"""
        self.__output_dir = directory

    @staticmethod
    def __min_to_mili(time):
        """convert minutes to miliseconds"""
        return time * 60 * 1000

    def trim(self, file, duration):
        """trim the length of an audiofile"""
        if "mp3" not in file:
            return None
        start_time = 0
        end_time = self.__min_to_mili(duration)
        song = AudioSegment.from_mp3(file)
        if duration == 0:
            return song
        return song[start_time:end_time]

    @staticmethod
    def __mkdir_pv(ensure_dir):
        """make a directory if it doesn't exist"""
        Path(ensure_dir).mkdir(parents=True, exist_ok=True)

    def __get_write_directory(self, directory):
        if directory == "NA/":
            return self.__output_dir
        return f"{self.__output_dir}{directory}"

    def __get_write_fullpath(self, directory, filename):
        return f"{self.__get_write_directory(directory)}{filename}"

    @staticmethod
    def __write_new_file(extracted_song, new_file):
        """write a trimmed file to a new file"""
        print(f"Writing file to: {new_file}")
        extracted_song.export(new_file, format="mp3")

    def write(self, directory, file, filename):
        """save a file to a location"""
        dest_dir = self.__get_write_directory(directory)
        self.__mkdir_pv(dest_dir)
        full_path = self.__get_write_fullpath(directory, filename)
        self.__write_new_file(file, full_path)

    def process_filename(self, filename):
        """adjust the filename based on loaded functions"""
        for method in self.__filename_map_hooks:
            filename = method(filename)
        return filename

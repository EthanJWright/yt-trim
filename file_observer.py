"""Observe states a file on the system can go through"""
from pathlib import Path
import time
import threading
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
class ModifiedDoneThread(threading.Thread):
    """Track when a file hasnt been modified for a second"""

    def __init__(self, handlers, modified_timers):
        threading.Thread.__init__(self)
        # dict of type { "last_modified": time, "event": event }
        self.__modified_timers = modified_timers
        self.__handlers = handlers

    def run(self):
        while len(self.__modified_timers) > 0:
            time.sleep(1)
            now = time.time()
            remove_timers = []
            for key in list(self.__modified_timers):
                value = self.__modified_timers[key]
                last_modified = value["last_modified"]
                if now - last_modified > 1:
                    for handler in self.__handlers:
                        handler(value["event"])
                    remove_timers.append(key)

            for timer in remove_timers:
                self.__modified_timers.pop(timer, None)


class FileObserver:
    """API to watch for files being downloaded"""

    def __init__(self, directory="./", patterns=None, case_sensitive=True):
        if patterns is None:
            patterns = []
        self.__on_handlers = {"on_modified_done": []}
        self.__directory = directory
        self.__handler = PatternMatchingEventHandler(patterns, "", True, case_sensitive)
        self.__observer = Observer()
        self.__watching = False
        self.__modified_timers = {}
        self.__modified_thread = None


    def set_directory(self, directory):
        """set directory to be ovserved"""
        self.__directory = directory

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
        self.__observer.schedule(self.__handler, self.__directory, True)
        self.__observer.start()

    def stop(self):
        """Stop observing the file system"""
        print("Shutting down file observation...")
        self.__modified_thread.join()
        self.__observer.stop()
        self.__observer.join()
        self.__watching = False

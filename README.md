# yt-trim

Download YouTube playlists and trim to a specific length

## Why

I'm currently using this tool to grab content that is quite long so that I can
trim it and then upload it to roll 20 for RPG sessions.

## Setup

Install requirements

```sh
python3 -m pip install -r requirements.txt
```

## Usage

```sh
python3 yt_trim.py --source=PLLBJrClJPlWJScARaoX_LIw1n3LiPoZZQ --duration=15
```

```sh

$ python3 yt_trim.py --help
usage: Download youtube videos as trimmed MP3s [--playlist]

optional arguments:
  -h, --help           show this help message and exit
  --source SOURCE      Youtube ID of source, video ID or playlist ID
  --duration DURATION  Duration of output file, in minutes
```

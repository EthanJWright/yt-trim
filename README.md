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

Set up the output and trim directories
```sh
mkdir -pv ./outputs ./sounds
```

## Using

```sh
python3 yt_trim.py --source=PLLBJrClJPlWJScARaoX_LIw1n3LiPoZZQ --duration=1
```

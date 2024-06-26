#!/bin/bash

docker run -d --rm --name discord-music-bot -v ./.env:/app/.env discord-music-bot
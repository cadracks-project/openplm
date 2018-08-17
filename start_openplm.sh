#!/usr/bin/env bash

xhost +local:openplm
docker start openplm
docker exec -it openplm /bin/bash

#!/usr/bin/env bash

home="${1:-$HOME}"

imageName="guillaume-florent/openplm:2.0.1"
containerName="openplm"
displayVar="$DISPLAY"

docker build --tag ${imageName} .

docker run  -it -d --name ${containerName}                  \
    -p 80:80                                                \
    -e DISPLAY=${displayVar}                                \
    --workdir="${home}"                                     \
    --volume="${home}:${home}"                              \
     -v=/tmp/.X11-unix:/tmp/.X11-unix ${imageName}          \
     /bin/bash

echo "Container ${containerName} was created."
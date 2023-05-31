#!/bin/bash

set -eu

Main() {

  ##############################################################################
  # DEFAULTS
  ##############################################################################

  local IMAGE_NAME=exadra37/googleplay-api-cli
  local VARIANT=debian
  local PYTHON_VERSION="3.7"
  local CONTAINER_USER=$(id -u)
  local COMMAND="developer"
  local BUILD_PATH=./
  local BACKGROUND_MODE="-it"
  local PORT_MAP="6000:5000"


  ##############################################################################
  # PARSE INPUT
  ##############################################################################

  if [ -f ./.env ]; then
      source ./.env
  fi

  for input in "${@}"; do
    case "${input}" in
      --tag )
          PYTHON_VERSION="${2? Missing Python version!!!}"
          shift 2
          ;;
      -d | --detached )
          BACKGROUND_MODE="--detach"
          shift 1
          ;;
      -p | --port-map )
          PORT_MAP=${2? Missing host port map for the container, eg: 3000:3000 !!!}
          shift 2
          ;;
      -u | --user )
          CONTAINER_USER=${2? Missing user for container!!!}
          shift 2
          ;;
      --variant )
          VARIANT="${2? Missing variant for docker image... eg: alpine}"
          shift 2
          ;;
      --build )
          sudo docker build \
              --file "${BUILD_PATH}"/"Dockerfile" \
              --build-arg "TAG=${PYTHON_VERSION}" \
              -t ${IMAGE_NAME} \
              "${BUILD_PATH}"

          exit 0
          ;;
      shell )
          COMMAND=zsh
          shift 1
          ;;
    esac
  done


  ##############################################################################
  # EXECUTION
  ##############################################################################


      # --volume "${PWD}"/.local/python-container:/home/developer/python \
  sudo docker run \
      --rm \
      ${BACKGROUND_MODE} \
      --user ${CONTAINER_USER} \
      --env-file .env \
      --volume "${PWD}"/../../data:/home/developer/workspace/data/scrapped \
      --volume "${PWD}"/../report/data:/home/developer/workspace/data/report \
      --volume "${PWD}":/home/developer/workspace \
      "${IMAGE_NAME}" \
      "${COMMAND}" ${@}
}

Main "${@}"

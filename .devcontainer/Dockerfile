FROM mcr.microsoft.com/devcontainers/python:3.11

ARG USERNAME=vscode

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        gcc \
        g++ \
        make \
        git \
        curl \
        wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER ${USERNAME}

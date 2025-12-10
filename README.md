# SafeAir Hardware

SafeAir Hardware is a python program that collect and send telemetry data to main backend

## Installation
```bash
sudo apt update
sudo apt install swig
sudo apt install liblgpio-dev
sudo apt install build-essential
sudo apt install libffi-dev
sudo apt install python3-dev
```

Use the package manager [uv](https://github.com/astral-sh/uv) to install dependencies.

```bash
uv sync
```

Create **config.json** from template

```bach
cp config.example.json config.json
``` 

## Usage

```bash
uv run python main.py
```
# SafeAir Hardware

SafeAir Hardware is a python program that collect and send telemetry data to main backend

## Installation

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
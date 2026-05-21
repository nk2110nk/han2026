#!/bin/bash
uv lock --upgrade-package ${1:-negmas-llm} && uv sync

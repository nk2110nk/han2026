@echo off
if "%1"=="" (
    uv lock --upgrade-package negmas-llm && uv sync
) else (
    uv lock --upgrade-package %1 && uv sync
)

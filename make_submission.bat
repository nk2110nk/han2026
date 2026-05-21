@echo off
REM Creates a submission zip file for the ANL 2026 competition
REM Excludes: examples, scenarios, report, tests, README.md, main.py, pyproject.toml, uv.lock, and dev files

set OUTPUT=submission.zip

REM Remove old submission if exists
if exist %OUTPUT% del %OUTPUT%

REM Create the zip file using tar (available on Windows 10+)
tar -a -cf %OUTPUT% ^
    --exclude=examples ^
    --exclude=images ^
    --exclude=scenarios ^
    --exclude=report ^
    --exclude=tests ^
    --exclude=README.md ^
    --exclude=main.py ^
    --exclude=pyproject.toml ^
    --exclude=uv.lock ^
    --exclude=.git ^
    --exclude=.venv ^
    --exclude=__pycache__ ^
    --exclude=.ruff_cache ^
    --exclude=.pytest_cache ^
    --exclude=.gitignore ^
    --exclude=.envrc ^
    --exclude=.envrc.local ^
    --exclude=.python-version ^
    --exclude=pyrightconfig.json ^
    --exclude=.pre-commit-config.yaml ^
    --exclude=make_submission.sh ^
    --exclude=make_submission.bat ^
    --exclude=update_package.sh ^
    --exclude=update_package.bat ^
    --exclude=update_all_packages.sh ^
    --exclude=update_all_packages.bat ^
    --exclude=dist ^
    --exclude=*.egg-info ^
    .

echo.
echo Created %OUTPUT%
echo.
echo To view contents, run: tar -tf %OUTPUT%

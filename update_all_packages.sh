#!/bin/bash
# Update all packages to their latest versions
echo "Updating all packages to their latest versions..."
uv lock --upgrade && uv sync
echo "All packages updated successfully!"

#!/bin/bash

# Script to rename PCD/BIN files to zero-padded format (e.g., 000001.pcd)
# Usage: ./rename_pcd_files.sh <directory> <extension>
# Example: ./rename_pcd_files.sh /path/to/files pcd

if [ $# -lt 1 ]; then
    echo "Usage: $0 <directory> [extension]"
    echo "Example: $0 /path/to/files pcd"
    echo "Default extension: pcd"
    exit 1
fi

DIR="$1"
EXT="${2:-pcd}"

if [ ! -d "$DIR" ]; then
    echo "Error: Directory $DIR does not exist"
    exit 1
fi

cd "$DIR" || exit 1

echo "Renaming *.$EXT files in $DIR to 6-digit zero-padded format..."

# Create a temporary directory for renamed files
TEMP_DIR=$(mktemp -d)

count=0
for file in *.$EXT; do
    if [ -f "$file" ]; then
        # Extract number from filename
        num=$(basename "$file" .$EXT)

        # Check if it's a valid number
        if [[ "$num" =~ ^[0-9]+$ ]]; then
            # Format to 6 digits with leading zeros
            new_name=$(printf "%06d.$EXT" "$((10#$num))")

            # Move to temp directory first to avoid conflicts
            mv "$file" "$TEMP_DIR/$new_name"
            ((count++))
        fi
    fi
done

# Move all files back from temp directory
mv "$TEMP_DIR"/*.$EXT . 2>/dev/null

# Remove temp directory
rmdir "$TEMP_DIR"

echo "Renamed $count files successfully"
echo "Sample files:"
ls *.$EXT | head -5

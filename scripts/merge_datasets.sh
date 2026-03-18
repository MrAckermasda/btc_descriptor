#!/bin/bash

# Script to merge two datasets (0 and 1) into dataset 3
# Merges PCD files and pose files with continuous numbering
# Usage: ./merge_datasets.sh

BASE_DIR="/home/lyl/btc_ws/src/btc_descriptor/poses/zzf_poses"
DIR_0="$BASE_DIR/1"
DIR_1="$BASE_DIR/1"
DIR_3="$BASE_DIR/4"
POSE_DIR="$BASE_DIR/pose_correct"

# Check if source directories exist
if [ ! -d "$DIR_0" ]; then
    echo "Error: Directory $DIR_0 does not exist"
    exit 1
fi

if [ ! -d "$DIR_1" ]; then
    echo "Error: Directory $DIR_1 does not exist"
    exit 1
fi

# Create target directory
mkdir -p "$DIR_3"

echo "Merging datasets 0 and 1 into 3..."
echo "=================================="

# Count files in each directory
count_0=$(ls "$DIR_0"/*.pcd 2>/dev/null | wc -l)
count_1=$(ls "$DIR_1"/*.pcd 2>/dev/null | wc -l)

echo "Dataset 0: $count_0 files"
echo "Dataset 1: $count_1 files"
echo "Total: $((count_0 + count_1)) files"
echo ""

# Copy files from directory 0 (keep original numbering)
echo "Copying files from dataset 0..."
cp "$DIR_0"/*.pcd "$DIR_3/" 2>/dev/null
echo "Done: $count_0 files copied"

# Copy and renumber files from directory 1
echo "Copying and renumbering files from dataset 1..."
copied=0
file_index=0
for file in $(ls "$DIR_1"/*.pcd | sort -V); do
    if [ -f "$file" ]; then
        # New number = file_index + count_0
        new_num=$((file_index + count_0))

        # Format to 6 digits
        new_name=$(printf "%06d.pcd" "$new_num")

        # Copy with new name
        cp "$file" "$DIR_3/$new_name"
        ((copied++))
        ((file_index++))
    fi
done
echo "Done: $copied files copied and renumbered"
echo ""

# Merge pose files
echo "Merging pose files..."
if [ -f "$POSE_DIR/0.txt" ] && [ -f "$POSE_DIR/1.txt" ]; then
    # Copy 0.txt content
    cat "$POSE_DIR/0.txt" > "$POSE_DIR/3.txt"

    # Append 1.txt content with adjusted line numbers
    while read -r line; do
        # Skip empty lines
        if [ -z "$line" ]; then
            continue
        fi

        # Split line into array
        read -ra cols <<< "$line"

        # First column is frame_id, adjust it
        old_id="${cols[0]}"
        new_id=$((old_id + count_0))

        # Output adjusted line
        echo -n "$new_id" >> "$POSE_DIR/3.txt"
        for ((i=1; i<${#cols[@]}; i++)); do
            echo -n " ${cols[$i]}" >> "$POSE_DIR/3.txt"
        done
        echo "" >> "$POSE_DIR/3.txt"

    done < "$POSE_DIR/1.txt"

    echo "Pose file created: $POSE_DIR/3.txt"
    echo "Total pose lines: $(wc -l < "$POSE_DIR/3.txt")"
else
    echo "Warning: Pose files not found, skipping pose merge"
fi

echo ""
echo "=================================="
echo "Merge completed successfully!"
echo "Output directory: $DIR_3"
echo "Total PCD files: $(ls "$DIR_3"/*.pcd 2>/dev/null | wc -l)"
echo ""
echo "First 5 files:"
ls "$DIR_3"/*.pcd | sort -V | head -5
echo "..."
echo "Last 5 files:"
ls "$DIR_3"/*.pcd | sort -V | tail -5

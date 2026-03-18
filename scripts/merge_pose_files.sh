#!/bin/bash

# Script to merge two pose files (0_fixed.txt and 1_fixed.txt) into 3.txt
# Adjusts frame IDs to be continuous
# Usage: ./merge_pose_files.sh

POSE_DIR="/home/lyl/btc_ws/src/btc_descriptor/poses/zzf_poses/pose_correct"
FILE_0="$POSE_DIR/1_renumbered.txt"
FILE_1="$POSE_DIR/1_renumbered.txt"
FILE_3="$POSE_DIR/4.txt"

# Check if source files exist
if [ ! -f "$FILE_0" ]; then
    echo "Error: File $FILE_0 does not exist"
    exit 1
fi

if [ ! -f "$FILE_1" ]; then
    echo "Error: File $FILE_1 does not exist"
    exit 1
fi

echo "Merging pose files..."
echo "=================================="

# Count lines in file 0
count_0=$(wc -l < "$FILE_0")
echo "File 0_fixed.txt: $count_0 lines"

# Count lines in file 1
count_1=$(wc -l < "$FILE_1")
echo "File 1_fixed.txt: $count_1 lines"

echo "Total: $((count_0 + count_1)) lines"
echo ""

# Create temporary file
TEMP_FILE=$(mktemp)

# Copy 0_fixed.txt content directly
cat "$FILE_0" > "$TEMP_FILE"

# Append 1_fixed.txt content with adjusted frame IDs
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
    echo -n "$new_id" >> "$TEMP_FILE"
    for ((i=1; i<${#cols[@]}; i++)); do
        echo -n " ${cols[$i]}" >> "$TEMP_FILE"
    done
    echo "" >> "$TEMP_FILE"

done < "$FILE_1"

# Move temp file to output
mv "$TEMP_FILE" "$FILE_3"

echo "=================================="
echo "Merge completed successfully!"
echo "Output file: $FILE_3"
echo "Total lines: $(wc -l < "$FILE_3")"
echo ""
echo "First 3 lines:"
head -3 "$FILE_3"
echo "..."
echo "Lines around transition (lines $((count_0 - 1)) to $((count_0 + 2))):"
sed -n "$((count_0 - 1)),$((count_0 + 2))p" "$FILE_3"
echo "..."
echo "Last 3 lines:"
tail -3 "$FILE_3"

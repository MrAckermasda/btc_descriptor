#!/usr/bin/env python3
"""
Script to renumber the first column of pose files with sequential indices.
Usage: python renumber_pose_file.py <input_file> <output_file>
"""

import sys
import os


def renumber_pose_file(input_file, output_file):
    """
    Read a pose file and renumber the first column with sequential indices (0, 1, 2, ...).

    Args:
        input_file: Path to input pose file
        output_file: Path to output pose file
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    with open(input_file, 'r') as f_in:
        lines = f_in.readlines()

    with open(output_file, 'w') as f_out:
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Split the line and replace first column with new index
            parts = line.split()
            if len(parts) > 0:
                parts[0] = str(idx)
                f_out.write(' '.join(parts) + '\n')

    print(f"Successfully renumbered {len(lines)} lines.")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python renumber_pose_file.py <input_file> <output_file>")
        print("Example: python renumber_pose_file.py input.txt output.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    renumber_pose_file(input_file, output_file)

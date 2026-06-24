import os
import sys
import json
import zipfile
import argparse


TAP_MANIFEST = {
    "id": "",
    "name": "",
    "version": "1.0.0",
    "entry_point": "",
    "description": "",
    "author": "",
}


def pack_tap(source_dir, output_path):
    if not os.path.isdir(source_dir):
        print(f"Error: {source_dir} is not a directory.")
        return False

    manifest_path = os.path.join(source_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"Error: {source_dir} does not contain manifest.json.")
        return False

    with open(manifest_path, 'r') as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: manifest.json is not valid JSON: {e}")
            return False

    required = ["id", "name", "entry_point"]
    for key in required:
        if key not in manifest:
            print(f"Error: manifest.json missing required field: {key}")
            return False

    if not output_path.endswith('.tap'):
        output_path += '.tap'

    if os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, source_dir)
                    zf.write(fpath, arcname)
        print(f"Created {output_path}")
        return True
    except Exception as e:
        print(f"Error creating .tap file: {e}")
        return False


def extract_tap(tap_path, target_dir):
    if not os.path.exists(tap_path):
        print(f"Error: {tap_path} not found.")
        return False

    app_id = os.path.splitext(os.path.basename(tap_path))[0]
    extract_dir = os.path.join(target_dir, app_id)

    os.makedirs(extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(tap_path, 'r') as zf:
            zf.extractall(extract_dir)
        print(f"Extracted {tap_path} to {extract_dir}")
        return True
    except Exception as e:
        print(f"Error extracting .tap file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="TechNote App Packer (.tap)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    pack_parser = subparsers.add_parser("pack", help="Pack a folder into .tap")
    pack_parser.add_argument("source_dir", help="Source app directory containing manifest.json")
    pack_parser.add_argument("output", help="Output .tap file path")

    extract_parser = subparsers.add_parser("extract", help="Extract a .tap file")
    extract_parser.add_argument("tap_file", help="Path to .tap file")
    extract_parser.add_argument("target_dir", help="Target directory for extraction")

    args = parser.parse_args()

    if args.command == "pack":
        pack_tap(args.source_dir, args.output)
    elif args.command == "extract":
        extract_tap(args.tap_file, args.target_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

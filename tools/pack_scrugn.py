#!/usr/bin/env python3
import argparse
import json
import os
import zipfile


def pack_scrugn(source_dir, output_path=None):
    source_dir = os.path.abspath(source_dir)
    manifest_path = os.path.join(source_dir, 'manifest.json')
    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found")
        return False
    with open(manifest_path) as f:
        manifest = json.load(f)
    name = manifest.get('name', os.path.basename(source_dir))
    if not output_path:
        output_path = os.path.join(os.getcwd(), f"{name}.scrugn")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(source_dir):
            for fname in files:
                fp = os.path.join(root, fname)
                arcname = os.path.relpath(fp, source_dir)
                z.write(fp, arcname)
    print(f"Created {output_path}")
    return True


def extract_scrugn(scrugn_path, output_dir=None):
    scrugn_path = os.path.abspath(scrugn_path)
    if not output_dir:
        name = os.path.splitext(os.path.basename(scrugn_path))[0]
        output_dir = os.path.join(os.getcwd(), name)
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(scrugn_path, 'r') as z:
        z.extractall(output_dir)
    print(f"Extracted to {output_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Pack or extract .scrugn plugin files")
    sub = parser.add_subparsers(dest='command')
    pack_parser = sub.add_parser('pack', help='Pack a directory into .scrugn')
    pack_parser.add_argument('source', help='Source directory with manifest.json')
    pack_parser.add_argument('-o', '--output', help='Output .scrugn path')
    extract_parser = sub.add_parser('extract', help='Extract .scrugn to directory')
    extract_parser.add_argument('scrugn', help='.scrugn file to extract')
    extract_parser.add_argument('-o', '--output', help='Output directory')
    args = parser.parse_args()
    if args.command == 'pack':
        pack_scrugn(args.source, args.output)
    elif args.command == 'extract':
        extract_scrugn(args.scrugn, args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Run DRAKON Editor's own pipeline (drn_reference.tcl) on many .drn files.

Usage:
  run_reference.py DRAKON_EDITOR_DIR OUT.jsonl ROOT_LABEL=DIR [ROOT_LABEL=DIR ...]

Example:
  run_reference.py /tmp/drakon_editor /tmp/reference.jsonl \
      drakon_editor=/tmp/drakon_editor drakon.tech.desktop=/tmp/drakon.tech.desktop

Writes one JSON object per diagram, with "origin" set to LABEL/relative/path.drn.
The .drn files are copied to a temporary directory first, because DRAKON
Editor may upgrade old files in place when it opens them.

Needs tclsh 8.6 with tcllib and the sqlite3 Tcl package
(Debian: apt-get install tcl tcllib libsqlite3-tcl).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.path.join(HERE, "drn_reference.tcl")


def run_file(editor_dir, path, timeout=300):
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "input.drn")
        shutil.copyfile(path, copy)
        proc = subprocess.run(["tclsh", DRIVER, editor_dir, copy], capture_output=True, timeout=timeout)
    records = []
    for line in proc.stdout.decode("utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return proc.returncode, proc.stderr.decode("utf-8", "replace"), records


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    editor_dir, out_path = os.path.abspath(sys.argv[1]), sys.argv[2]
    roots = [arg.split("=", 1) for arg in sys.argv[3:]]
    total = failed = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for label, root in roots:
            for path in sorted(glob.glob(os.path.join(root, "**", "*.drn"), recursive=True)):
                origin = label + "/" + os.path.relpath(path, root)
                try:
                    code, err, records = run_file(editor_dir, path)
                except subprocess.TimeoutExpired:
                    code, err, records = -1, "timeout", []
                if code != 0:
                    failed += 1
                    out.write(json.dumps({"origin": origin, "file_error": err.strip()[-2000:]}, ensure_ascii=False) + "\n")
                for record in records:
                    record["origin"] = origin
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total += 1
    print("diagrams:", total, "files that failed to run:", failed)


if __name__ == "__main__":
    main()

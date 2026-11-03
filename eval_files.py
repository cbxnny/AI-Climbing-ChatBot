"""
File handling shared by the evaluation scripts (run_adversarial.py, run_heldout.py
and diagnose_filter.py).

"""

import argparse
import os
import re
import sys


def _tag_type(value):
    # argparse also runs this on the default, so an empty tag (no tag) must be accepted.
    if value and not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", value):
        raise argparse.ArgumentTypeError(
            "use only letters, digits, - and _ (at most 30 characters)")
    return value


def add_output_arguments(parser):
    """Add --tag and --overwrite to an argument parser."""
    parser.add_argument("--tag", type=_tag_type, default="", metavar="NAME",
                        help="write results_NAME.md style files instead of replacing earlier results")
    parser.add_argument("--overwrite", action="store_true",
                        help="replace output files that already exist")


def tagged(name, tag=""):
    """tagged("results.md", "run4") gives "results_run4.md". Without a tag the name is unchanged."""
    if not tag:
        return name
    stem, ext = os.path.splitext(name)
    return f"{stem}_{tag}{ext}"


def prepare_outputs(names, overwrite=False):
    """
    Call before the first API request. If any output file exists, print which ones
    and exit, so nothing has been spent yet. With overwrite=True the old files are
    deleted, so every run starts clean and a log never grows across runs.
    """
    existing = [name for name in names if os.path.exists(name)]
    if not existing:
        return
    if overwrite:
        for name in existing:
            os.remove(name)
        return
    print("These output files already exist and would be replaced:")
    for name in existing:
        print(f"  {name}")
    print("Nothing was run. Add --tag NAME to write a separate set of files, "
          "or --overwrite to replace these.")
    sys.exit(1)


def console_safe():
    """
    Stop a prompt with unusual characters from crashing a long run when the console
    or a redirected file cannot encode it (for example cp1252 on Windows).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="replace")

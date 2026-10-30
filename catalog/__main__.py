"""python3 -m catalog <check|verify|build|pr-scope> ...

  check                      validate every apps/*.json offline
  verify [ID|FILE ...]       download artifacts and inspect them (default: all)
  build [--out DIR]          write the GitHub Pages site (default: _site)
  pr-scope BASE              fail if the diff from BASE touches more than apps/
"""
import argparse
import pathlib
import subprocess
import sys

from . import artifacts, records, site


def cmd_check(_args) -> int:
    loaded, problems = records.load_all()
    for name, errors in problems.items():
        for error in errors:
            print(f"apps/{name}: {error}")
    print(f"{len(loaded)} valid, {len(problems)} invalid")
    return 1 if problems else 0


def cmd_verify(args) -> int:
    loaded, problems = records.load_all()
    if problems:
        return cmd_check(args)
    wanted = {pathlib.Path(item).stem for item in args.targets}
    failed = 0
    for record in loaded:
        if wanted and record["id"] not in wanted:
            continue
        errors = artifacts.verify(record)
        print(f"{'FAIL' if errors else 'ok  '} {record['id']} {record['version']}")
        for error in errors:
            print(f"     {error}")
        failed += bool(errors)
    return 1 if failed else 0


def cmd_build(args) -> int:
    loaded, problems = records.load_all()
    if problems:
        return cmd_check(args)
    document = site.build(loaded, pathlib.Path(args.out))
    print(f"wrote {args.out} ({document['count']} apps)")
    return 0


def cmd_pr_scope(args) -> int:
    changed = subprocess.run(["git", "diff", "--name-only", f"{args.base}...HEAD"],
                             capture_output=True, text=True, check=True).stdout.split()
    outside = [name for name in changed if not (name.startswith("apps/") and name.endswith(".json")
                                                and name.count("/") == 1)]
    for name in outside:
        print(f"outside apps/: {name}")
    apps = [name for name in changed if name not in outside]
    print("changed records: " + (" ".join(apps) or "none"))
    return 1 if outside else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="catalog", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    p = sub.add_parser("verify"); p.add_argument("targets", nargs="*"); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("build"); p.add_argument("--out", default="_site"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("pr-scope"); p.add_argument("base"); p.set_defaults(fn=cmd_pr_scope)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

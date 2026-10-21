#!/usr/bin/env python3
"""Serialize host experiments and retain exact lease intervals."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def lease(label, receipt):
    receipt = Path(receipt)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    if receipt.exists():
        raise FileExistsError(f"Preserve prior lease receipt: {receipt}")
    record = {"label": label, "pid": os.getpid(), "requested_utc": now(),
              "lock": str(ROOT / '.measurement.lock')}
    with (ROOT / '.measurement.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        record.update(acquired_utc=now(), acquired_monotonic_ns=time.monotonic_ns())
        receipt.write_text(json.dumps(record, indent=2) + '\n')
        try:
            yield record
        except BaseException as error:
            record['error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            record.update(released_utc=now(), released_monotonic_ns=time.monotonic_ns())
            receipt.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('a command is required')
    with lease(args.label, args.receipt) as record:
        record['command'] = command
        result = subprocess.run(command)
        record['returncode'] = result.returncode
    raise SystemExit(result.returncode)

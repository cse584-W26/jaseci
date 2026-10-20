"""Own-process manager for copied SNB/TPC-C SQLAlchemy baseline applications.

`plan` only prints configuration. Starting never loads or resets a database.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get('REPRO_BASELINE_PYTHON', str(ROOT / 'runtime/venv314/bin/python'))).expanduser().absolute()
PORTS = {'snb': 18113, 'tpcc': 18115}


def config(bench):
    return {
        'bench': bench,
        'service': f'optional-sqlalchemy-{bench}',
        'port': PORTS[bench],
        'cwd': str(ROOT / f'benchmark/{bench}/sqlalchemy'),
        'command': [str(PYTHON), '-m', 'uvicorn', 'app:app', '--host',
                    '127.0.0.1', '--port', str(PORTS[bench]), '--no-access-log'],
        'environment': {
            'PYTHONUNBUFFERED': '1',
            'SNB_DSN' if bench == 'snb' else 'TPCC_DSN':
                f'postgresql+psycopg://postgres@127.0.0.1:55436/{bench}',
        },
        'ready_url': f'http://127.0.0.1:{PORTS[bench]}/docs',
    }


def paths(cfg):
    return (ROOT / f"logs/{cfg['service']}.pid.json",
            ROOT / f"logs/{cfg['service']}-launch.json")


def process_start(pid):
    # /proc stat field22: start ticks; comm can contain spaces/parentheses.
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


def owned_process(record, cfg):
    pid = record['pid']
    try:
        cmd = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        cmd = [v.decode() for v in cmd if v]
        if not cmd:
            return False
        if process_start(pid) != record['start_ticks']:
            raise RuntimeError(f'PID {pid} has been reused; refusing to signal')
        if cmd != cfg['command'] or Path(f'/proc/{pid}/cwd').resolve() != Path(cfg['cwd']):
            raise RuntimeError(f'Process {pid} does not match this owned application')
        if os.getpgid(pid) != pid:
            raise RuntimeError(f'Process {pid} is not its own process group')
        return True
    except (FileNotFoundError, ProcessLookupError):
        return False


def stop(cfg):
    state, _ = paths(cfg)
    if not state.exists():
        print(f"{cfg['service']}: no tracked process", flush=True)
        return
    record = json.loads(state.read_text())
    if owned_process(record, cfg):
        os.killpg(record['pid'], signal.SIGTERM)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and owned_process(record, cfg):
            time.sleep(.2)
        if owned_process(record, cfg):
            raise RuntimeError('Owned server did not terminate within 15 seconds; state retained')
    state.unlink()
    print(f"{cfg['service']}: stopped", flush=True)


def start(cfg):
    state, latest = paths(cfg)
    if state.exists():
        record = json.loads(state.read_text())
        if owned_process(record, cfg):
            raise RuntimeError(f"Service already running PID {record['pid']}; stop it explicitly")
        state.unlink()
    # Confirm the chosen port is unused without touching another service.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(('127.0.0.1', cfg['port']))
        except OSError as exc:
            raise RuntimeError(f"Port {cfg['port']} unavailable; no process was started") from exc
    env = os.environ.copy()
    env.update(cfg['environment'])
    env.pop('PROF_TIMERS', None)
    stamp = time.strftime('%Y%m%dT%H%M%S')
    log = ROOT / f"logs/{cfg['service']}-{stamp}.log"
    with log.open('x') as handle:
        proc = subprocess.Popen(cfg['command'], cwd=cfg['cwd'], env=env,
                                stdout=handle, stderr=subprocess.STDOUT,
                                start_new_session=True)
    record = {**cfg, 'pid': proc.pid, 'start_ticks': process_start(proc.pid),
              'log': str(log), 'started_unix': time.time()}
    state.write_text(json.dumps(record, indent=2) + '\n')
    latest.write_text(json.dumps(record, indent=2) + '\n')
    try:
        for _ in range(120):
            if proc.poll() is not None:
                raise RuntimeError(f'Server exited {proc.returncode}; see {log}')
            try:
                with urllib.request.urlopen(cfg['ready_url'], timeout=2) as response:
                    if response.status == 200:
                        print(f"{cfg['service']}: ready PID {proc.pid}; log {log}", flush=True)
                        return
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError(f'HTTP startup timeout; see {log}')
    except BaseException:
        stop(cfg)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'start', 'stop', 'status'])
    parser.add_argument('bench', choices=list(PORTS))
    args = parser.parse_args()
    cfg = config(args.bench)
    if args.action == 'plan':
        print(json.dumps(cfg, indent=2))
        return
    (ROOT / 'logs').mkdir(exist_ok=True)
    lock = ROOT / f"logs/{cfg['service']}.lock"
    with lock.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'start':
            start(cfg)
        elif args.action == 'stop':
            stop(cfg)
        else:
            state, _ = paths(cfg)
            running = state.exists() and owned_process(json.loads(state.read_text()), cfg)
            print(json.dumps({'service': cfg['service'], 'running': bool(running)}))


if __name__ == '__main__':
    main()

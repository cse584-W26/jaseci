"""Run the original TPC-C loader against explicitly supplied isolated DSNs."""
import argparse,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--admin-dsn',required=True);p.add_argument('--dsn',required=True);p.add_argument('--data',default=str(ROOT/'benchmark/tpcc/data'));a=p.parse_args()
spec=importlib.util.spec_from_file_location('loader',ROOT/'benchmark/tpcc/postgres/loader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ADMIN_DSN=a.admin_dsn;m.DSN=a.dsn
sys.argv=[sys.argv[0],'--data',a.data]
m.main()

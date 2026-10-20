import argparse,importlib.util,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--admin-dsn',default='postgresql://postgres@127.0.0.1:55436/littleX');p.add_argument('--dsn',default='postgresql://postgres@127.0.0.1:55436/snb');p.add_argument('--data',default=str(root/'data/social_network-sf1-CsvBasic-LongDateFormatter'));a=p.parse_args()
spec=importlib.util.spec_from_file_location('snb_pg_loader',root/'benchmark/snb/postgres/loader.py');loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
loader.ADMIN_DSN=a.admin_dsn;loader.DSN=a.dsn
sys.argv=[sys.argv[0],'--data',a.data];loader.main()

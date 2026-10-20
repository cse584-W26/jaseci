"""Original SF1 Neo4j loader with explicit dedicated Bolt endpoint."""
import argparse,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--uri',default='bolt://127.0.0.1:17687');p.add_argument('--data',default=str(ROOT/'data/social_network-sf1-CsvBasic-LongDateFormatter'));a=p.parse_args()
assert a.uri.startswith(('bolt://127.0.0.1:17687','neo4j://127.0.0.1:17687')), 'Use the dedicated reproduction Neo4j endpoint'
spec=importlib.util.spec_from_file_location('snb_neo4j_loader',ROOT/'benchmark/snb/neo4j/loader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.URI=a.uri;sys.argv=[sys.argv[0],'--data',a.data];m.main()

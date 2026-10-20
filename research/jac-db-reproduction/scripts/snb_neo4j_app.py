"""Unmodified Neo4j handlers, dedicated reproduction driver URI."""
import importlib.util,os
from pathlib import Path
from neo4j import GraphDatabase
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('snb_neo4j_original',ROOT/'benchmark/snb/neo4j/app.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.driver.close()
m.driver=GraphDatabase.driver(os.environ.get('SNB_NEO4J_URI','bolt://127.0.0.1:17687'),auth=('neo4j','snbpassword'))
app=m.app

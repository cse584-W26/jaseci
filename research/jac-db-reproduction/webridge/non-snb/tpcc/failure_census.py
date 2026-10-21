#!/usr/bin/env python3
"""Classify observed stage failures from retained logs without inferring SQL fusion."""
import hashlib,json,pathlib,time
H=pathlib.Path(__file__).resolve().parent;rows=[]
for current in json.loads((H/'case-status.json').read_text()):
 if current['status']!='failed-stage':continue
 case=pathlib.Path(current['case']);stages=current.get('stages',[]);failed=next((s for s in reversed(stages)if s.get('returncode')),stages[-1]if stages else{});stage=failed.get('stage',current.get('failure'));stagepath=pathlib.Path(failed['path'])if failed.get('path')else None;logs=[]
 for folder in ([stagepath]if stagepath else[])+[case]:
  if folder and folder.exists():
   selected=[folder/'stdout.log',folder/'stderr.log']if folder!=case else list(folder.glob('synth-*/stderr.log'))
   for p in selected:
    if p.exists()and p not in logs:logs.append(p)
 text='\n'.join(p.read_text(errors='replace')for p in logs);category='retained_stage_failure';reason=current.get('failure')
 if'Unsupported symbolizing behavior of interned String'in text:category='native_interned_input_string';reason='Native VM rejects an interned String passed to System.symbolize and exits134'
 elif'caught unhandled signal 11'in text:category='native_vm_replay_crash';reason='Native replay exits134; retained hs_err Java frames locate the failing operation'
 elif'ParseProblemException'in text and'Found "@"'in text:category='symbolic_bigdecimal_expression';reason='Generated BigDecimal parameter expression contains an unparsed field marker; numeric-model-boundary.json provides the actual expression/scales/source'
 elif'NumberFormatException'in text and'For input string: "inf"'in text:category='native_infinity_literal_frontend_parse';reason='Native replay completed, but StoredProcedureManager parses native inf with Float.parseFloat and throws NumberFormatException'
 elif'($BIG_DECIMAL$'in text:category='symbolic_bigdecimal_formal_parameter';reason='Emitted procedure uses a BigDecimal expression as a formal parameter; MySQL rejects CREATE PROCEDURE1064'
 frames=[]
 if stagepath:
  for crash in stagepath.glob('hs_err_pid*.log'):frames.extend(line.strip()for line in crash.read_text(errors='replace').splitlines()if'istate->_method'in line)
 report=next(case.glob('record-*/report.json'),None);record=json.loads(report.read_text())if report else None
 rows.append({'family':'tpcc','workload':current['workload'],'program':current['program'],'variant':current['variant'],'case':str(case),'stage':stage,'stage_returncode':failed.get('returncode'),'category':category,'observed_reason':reason,'logs':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in logs],'java_crash_frames':frames[:12],'recording_report':str(report)if report else None,'recorded_api_calls':record.get('region',{}).get('source_calls')if record else None,'pipeline':current.get('pipeline'),'source_manifest':current.get('source_manifest')})
(H/'stage-failures.json').write_text(json.dumps({'generated_wall_ns':time.time_ns(),'cases':rows,'interpretation':'Failures precede accepted optimization; no claim about SQL fusion is assigned to a failed capture/synthesis/install stage'},indent=2));print(len(rows),'actual terminal failures')

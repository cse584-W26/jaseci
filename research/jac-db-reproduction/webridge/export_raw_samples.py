#!/usr/bin/env python3
"""Save already-collected latency samples after the benchmark finishes."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;D=R/'paper-driver'
p=D/'src/main/java/webench/meta/perf/StatisticsPrintHelper.java';s=p.read_text()
old='''    for (APIType apiType : statistics.durations.keySet()) {
      StringBuilder content = new StringBuilder();'''
new='''    for (APIType apiType : statistics.durations.keySet()) {
      // Post-run artifact export only: measurement and request paths are unchanged.
      StringBuilder rawSamples = new StringBuilder("period,sample,elapsed_ns\\n");
      List<List<Long>> rawPeriods = statistics.durations.get(apiType);
      for (int period = 0; period < rawPeriods.size(); period++) {
        List<Long> rawValues = rawPeriods.get(period);
        for (int sample = 0; sample < rawValues.size(); sample++) {
          rawSamples.append(period).append(",").append(sample).append(",")
              .append(rawValues.get(sample)).append("\\n");
        }
      }
      writeToFile(baseDir + "/raw-" + apiType + ".csv", rawSamples.toString());
      StringBuilder content = new StringBuilder();'''
if 'Post-run artifact export only' not in s:
 assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
receipt=D/'paper-repair-receipt.json';x=json.loads(receipt.read_text());note='Post-run export of existing per-request latency samples; request execution and timing boundaries unchanged'
if note not in x['changes']:x['changes'].append(note)
x['files_sha256'][str(p.relative_to(D))]=hashlib.sha256(p.read_bytes()).hexdigest();receipt.write_text(json.dumps(x,indent=2)+'\n')

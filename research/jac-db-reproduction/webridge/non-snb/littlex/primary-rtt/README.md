# Primary SQL round-trip measurements

The primary value is the median of each request’s sum of outer SQL command round-trip durations. Each duration starts when the proxy receives the complete MySQL COM_QUERY command and ends when it forwards and drains the final response packet to the client socket. The MySQL response parser consumes every result set and terminal status packet. CALL contributes one outer duration.

The timer’s two SHOW SESSION STATUS commands mark each request. Both status commands and connection initialization are outside the measured sum. Every selected command has one complete received response and one complete delivered response. Command counts equal the request’s session Questions delta, and CALL counts equal Com_call_procedure. The owned application JDBC connection is matched through its actual MySQL server connection ID.

The compact proxy retains SQL, command timestamps, completion timestamps/counts and lifecycle evidence. Packet, frame and row event logs are filtered; the validated parser and byte forwarding are unchanged. Full response contents are retained separately by the timer and checked against the source fixture oracle. Initial and final committed business state is checked independently for every executable cell.

Application elapsed measurements remain secondary under compact instrumentation. Earlier calibration-only quiet measurements are retained as partial application evidence.

`run_complete.py --out NEW_DIRECTORY` collects 360 latency cells plus120 references in short shared-lease groups. `finish.py` publishes `../normalized-rtt-results.json` and `../rtt-cycle-evidence.json`. Genuine compiler-stage failures retain their stage receipts and null median.

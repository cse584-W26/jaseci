"""Tests for JAC_GC_FREEZE_WARMUP (post-warmup gc freeze + gen-2 tuning).

Boot-time gc.freeze cannot cover the request working set (it does not
exist yet); this flag re-freezes N seconds after boot. Measured effect:
feed p99 242ms -> 61ms (gen-2 pauses moved off the request path).
"""

import gc;
import os;
import time;
import from jaclang.scale.jserver.jfast_api { _arm_warmup_gc_freeze }

glob FLAG = "JAC_GC_FREEZE_WARMUP",
     GEN2 = "JAC_GC_FREEZE_WARMUP_GEN2";


def _cleanup(prev_thresh: tuple, prev_env: dict) {
    gc.set_threshold(*prev_thresh);
    gc.unfreeze();
    for (k, v) in prev_env.items() {
        if v is None {
            os.environ.pop(k, None);
        } else {
            os.environ[k] = v;
        }
    }
}


test "unset flag is a no-op" {
    prev = {FLAG: os.environ.pop(FLAG, None), GEN2: os.environ.pop(GEN2, None)};
    prev_thresh = gc.get_threshold();
    try {
        before = gc.get_freeze_count();
        _arm_warmup_gc_freeze();
        time.sleep(0.05);
        assert gc.get_freeze_count() == before;
        assert gc.get_threshold() == prev_thresh;
    } finally {
        _cleanup(prev_thresh, prev);
    }
}

test "freeze fires after the delay and sets gen2 threshold" {
    prev = {FLAG: os.environ.get(FLAG), GEN2: os.environ.get(GEN2)};
    prev_thresh = gc.get_threshold();
    try {
        os.environ[FLAG] = "0.05";
        os.environ[GEN2] = "100";
        before = gc.get_freeze_count();
        _arm_warmup_gc_freeze();
        deadline = time.time() + 5.0;
        while time.time() < deadline and gc.get_freeze_count() <= before {
            time.sleep(0.02);
        }
        assert gc.get_freeze_count() > before , "warmup freeze never fired";
        (g0, g1, g2) = gc.get_threshold();
        assert g2 == 100 , f"gen2 threshold not applied: {g2}";
        assert (g0, g1) == prev_thresh[:2] , "gen0/gen1 thresholds must not change";
    } finally {
        _cleanup(prev_thresh, prev);
    }
}

test "malformed values fail loud" {
    prev = {FLAG: os.environ.get(FLAG), GEN2: os.environ.get(GEN2)};
    prev_thresh = gc.get_threshold();
    try {
        os.environ[FLAG] = "soon";
        raised = False;
        try {
            _arm_warmup_gc_freeze();
        } except ValueError {
            raised = True;
        }
        assert raised , "non-numeric JAC_GC_FREEZE_WARMUP must raise";

        os.environ[FLAG] = "0.05";
        os.environ[GEN2] = "lots";
        raised = False;
        try {
            _arm_warmup_gc_freeze();
        } except ValueError {
            raised = True;
        }
        assert raised , "non-int JAC_GC_FREEZE_WARMUP_GEN2 must raise";
    } finally {
        _cleanup(prev_thresh, prev);
    }
}

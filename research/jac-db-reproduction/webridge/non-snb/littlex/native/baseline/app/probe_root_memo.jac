"""ITEM2 gate: JAC_ROOT_MEMO stale-entry check.
Instantiates JacScaleUserManager directly against this app's Postgres
identity store (same DB the live server uses), warms the memo for a real
seeded user, resets that user's root, and confirms the NEXT get_root_id
call returns the fresh root_id, not the memoized stale one.
"""
import os;
import from jaclang.scale.identity.user_manager { JacScaleUserManager }

with entry {
    os.environ['JAC_ROOT_MEMO'] = '1';
    um = JacScaleUserManager(base_path='.');
    uname = 'user_5';

    root1 = um.get_root_id(uname);
    print(f"root before reset: {root1}");
    assert root1 is not None;

    # memo hit path: same call, no DB round trip, must match
    root1b = um.get_root_id(uname);
    assert root1b == root1, "memo hit returned a different value than the DB read";
    print("memo-hit consistency: OK");

    new_root = um.reset_root(uname);
    print(f"reset_root -> {new_root}");
    assert new_root is not None;
    assert new_root != root1, "reset_root did not actually change the root_id";

    root2 = um.get_root_id(uname);
    print(f"root after reset: {root2}");
    assert root2 == new_root, (
        f"STALE MEMO: get_root_id returned {root2}, expected fresh {new_root}"
    );
    print("STALE-ENTRY GATE: PASS");
}

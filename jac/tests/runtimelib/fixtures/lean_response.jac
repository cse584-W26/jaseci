"""Server fixture for the default-off `api_lean_response` flag tests.

Walkers cover the three response shapes the flag has to handle:

  * `one_report` -- exactly one dict report (with a `server_total_ms`
    key and a serialized node) -> the unwrap-to-bare-body case.
  * `two_reports` -- two dict reports -> must keep the full envelope.
  * `scalar_report` -- one non-dict report -> must keep the full envelope.
"""

node Item {
    has name: str = "";
}


walker:priv one_report {
    has reports: list = [];

    can run with Root entry {
        fresh = here ++> Item(name="solo");
        report {"server_total_ms": 12.5, "feed": [fresh]};
    }
}


walker:priv two_reports {
    has reports: list = [];

    can run with Root entry {
        report {"first": 1};
        report {"second": 2};
    }
}


walker:priv scalar_report {
    has reports: list = [];

    can run with Root entry {
        report 42;
    }
}

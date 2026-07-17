"""Two-root cross-root graph app for the GTI-cache mongo e2e gate.

Walker set mirrors jac/tests/runtimelib/fixtures/cross_root_topo_index.jac
(the canonical cross-root fixture), plus `gti_cache_probe`, which reports the
server process's decoded-GTI cache counters so the test can prove the cache
actually engaged on the server side.
"""

node Profile {
    has username: str = "";
}

node Tweet {
    has content: str = "";
}

edge Follow {}
edge Post {}


walker:priv setup_profile_only {
    has username: str = "";
    has reports: list = [];

    can run with Root entry {
        existing = [-->[?:Profile]];
        if existing {
            visit existing;
        } else {
            fresh = here ++> Profile(username=self.username);
            grant(fresh, level=ConnectPerm);
            visit fresh;
        }
    }

    can apply with Profile entry {
        if self.username {
            here.username = self.username;
        }
        report jid(here);
    }
}


walker:priv post_tweet {
    has content: str = "";
    has reports: list = [];

    can run with Root entry {
        visit [-->[?:Profile]];
    }

    can make with Profile entry {
        tweet = Tweet(content=self.content);
        here +>: Post() :+> tweet;
        grant(tweet, level=ConnectPerm);
        report jid(tweet);
    }
}


walker:priv follow_target {
    has target_id: str = "";
    has reports: list = [];

    can run with Root entry {
        visit [-->[?:Profile]];
    }

    can act with Profile entry {
        target_profile = & (self.target_id);
        here +>: Follow() :+> target_profile;
        report "ok";
    }
}


walker:priv query_follow_chain {
    """Forward chain: my Follow edges -> their Profile -> their Tweets."""
    has reports: list = [];

    can run with Root entry {
        prof_list = [-->[?:Profile]];
        if not prof_list {
            report 0;
            return;
        }
        me = prof_list[0];
        tweets = [me->:Follow:->[?:Profile]-->[?:Tweet]];
        report len(tweets);
    }
}


walker:priv gti_cache_probe {
    """Report the server-process decoded-GTI cache counters."""
    has reports: list = [];

    can run with Root entry {
        import from jaclang.runtimelib.gti_cache { cache_stats }
        report cache_stats();
    }
}

"""Little X - Headless backend entry for the DBHarness benchmark server.

No frontend. Importing the app walkers here brings them into the served module
so jac-cloud exposes each as `POST /walker/<name>`. The `import_data` seed
walker lives in a separate module (`import_data.jac`) — uncomment its import
once that file exists.
"""

import from app {
    noop_probe,
    get_profile,
    get_profile_by_id,
    load_feed,
    load_feed_page,
    load_feed_leaf,
    load_feed_chain,
    load_feed_page_chain,
    create_tweet,
    follow_user,
    like_tweet
}

import from import_data { seed_profile, seed_tweet, seed_follow }

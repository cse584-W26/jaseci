"""SNB Interactive on jac (LTI arm). ONE service-account root owns the whole
social network: SNB's client queries arbitrary persons (the benchmark's
"user" is the driver, not a person), so littleX's per-user-root model does
not apply - persons are plain nodes, updates run on the same service root.
Entry into the graph is by jid (driver holds id->jid maps minted at load).

Undirected KNOWS is stored as a directed edge + traversed both directions
in every query (union of -> and <-).
"""

# burden: bench=snb feature=schema arm=jac-lti
# burden: dbloc=42 notations=[jac] entity-reps=1 hand-tuning=0

import time;
import datetime;
import from typing { cast }

def _now_ms -> int {
    return int(time.time() * 1000);
}

edge Knows {
    has creationDate: int = 0;
}
edge IsLocatedIn {}
edge HasCreator {}
edge ReplyOf {}
edge ContainerOf {}
edge HasMember {
    has joinDate: int = 0;
}

node Place {
    has place_id: int = 0,
        name: str = "",
        place_type: str = "";
}

node Person {
    has person_id: int = 0,
        firstName: str = "",
        lastName: str = "",
        gender: str = "",
        birthday: int = 0,
        creationDate: int = 0,
        locationIP: str = "",
        browserUsed: str = "";
}

node Forum {
    has forum_id: int = 0,
        title: str = "",
        creationDate: int = 0;
}

node Post {
    has post_id: int = 0,
        imageFile: str = "",
        creationDate: int = 0,
        locationIP: str = "",
        browserUsed: str = "",
        language: str = "",
        content: str = "",
        length: int = 0;
}

node Comment {
    has comment_id: int = 0,
        creationDate: int = 0,
        locationIP: str = "",
        browserUsed: str = "",
        content: str = "",
        length: int = 0;
}

# ---- short reads ----------------------------------------------------------

# burden: bench=snb feature=is1 arm=jac-lti
# burden: dbloc=14 notations=[jac] entity-reps=1 hand-tuning=0
walker is1_profile {
    has person_jid: str = "";

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        cities = [p->:IsLocatedIn:->[?:Place]];
        city_id = -1;
        if cities {
            city_id = cities[0].place_id;
        }
        report {
            "firstName": p.firstName, "lastName": p.lastName,
            "birthday": p.birthday, "locationIP": p.locationIP,
            "browserUsed": p.browserUsed, "cityId": city_id,
            "gender": p.gender, "creationDate": p.creationDate
        };
    }
}

# burden: bench=snb feature=is2 arm=jac-lti
# burden: dbloc=30 notations=[jac] entity-reps=1 hand-tuning=0
# burden: bench=snb feature=is2 arm=jaseci-pg-cte (JAC_CTE_TRAVERSE=1)
# burden: dbloc=36 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning 1: the app hands a top-K builtin the edge type, both message
#  archetypes with their tie-break field names, the sort field, an opened
#  bound and the limit - the ORDER BY / LIMIT the walker already spells out
#  as a sort+slice, restated for the engine; same class as ic2's.
#  Item #23 removed what used to be hand-tuning 2 here: the denormalised
#  creator_jid field and its hand-built index are now a column + index the
#  RUNTIME grows and trigger-maintains for the HasCreator hop.
#  Item #22 removed what used to be the rootcol arm's hand-tuning: the
#  denormalised root_post_jid field on Comment, its by-hand maintenance on
#  every comment-create path and its bulk-load backfill are now a
#  root_of_ReplyOf column the runtime grows, backfills with one recursive
#  CTE and trigger-maintains; the app asks with jroot_many.)
walker is2_recent_messages {
    has person_jid: str = "";

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        msgs: list = [];
        # ONE ordered index scan per message type for the whole first
        # step: this person's 10 most recent Posts+Comments, cut in SQL
        # against the (endpoint, creationDate DESC) mirror index the
        # RUNTIME grows for the HasCreator hop (item #23). The plain-hop
        # form instead hydrates EVERY message this person ever wrote (~500
        # at SF1) to keep 10.
        # IS2 has no date bound, so the builtin's bound is opened to
        # bigint max - it rides into the index cond as an open-ended
        # range and the plan stays an ordered Index Scan that stops at
        # 10 (measured: 20 buffers, 0.06ms warm).
        #
        # The builtin's internal tie-break is (creationDate DESC, id ASC)
        # but IS2's is (creationDate DESC, id DESC), so the sort below is
        # kept and applied to whatever comes back: output order is exactly
        # IS2's either way. The residual is selection at the 10/11
        # boundary if two of a person's messages share a creationDate -
        # measured over the whole SF1 fixture: 762 such tie groups exist,
        # ZERO of them inside any creator's top 11, so no param can
        # observe it here. A tie-direction argument on the builtin would
        # close it properly.
        for mid in jtopk([jid(p)], "HasCreator",
                         [(Post, "post_id"), (Comment, "comment_id")],
                         "creationDate", 9223372036854775807, 10) {
            m = jobj(mid);
            if isinstance(m, Post) {
                msgs.append(["post", m.creationDate, m.post_id, m]);
            } elif isinstance(m, Comment) {
                msgs.append(["comment", m.creationDate, m.comment_id, m]);
            }
        }
        msgs.sort(key=lambda (e: list) { (-e[1], -e[2]); });
        top10 = msgs[:10];
        # Every surviving comment's root Post in ONE builtin call: the
        # runtime grows and trigger-maintains a root_of_ReplyOf column on
        # Comment's mirror (item #22, ensure_root_column - write-once chain
        # shape proved by probes, any re-parent poisons the claim) and falls
        # back to one recursive CTE when the column cannot answer. The app
        # no longer declares, sets or backfills a denormalised field.
        root_jid: dict = {};
        cnodes: list = [e[3] for e in top10 if e[0] == "comment"];
        if cnodes {
            rj_list = jroot_many(cnodes, "ReplyOf", Post);
            for (ci, cn) in enumerate(cnodes) {
                if rj_list[ci] {
                    root_jid[jid(cn)] = rj_list[ci];
                }
            }
        }
        # Batched response shaping: load the root posts, then ONE batched
        # HasCreator edge query over them for authors -- the exact author_of
        # idiom ic2 uses.
        root_of: dict = {};
        author_of: dict = {};
        rjids: list = [];
        for rj in root_jid.values() {
            if rj not in rjids {
                rjids.append(rj);
            }
        }
        if rjids {
            for rj in rjids {
                root_of[rj] = jobj(rj);
            }
            rposts = [o for o in root_of.values() if isinstance(o, Post)];
            if rposts {
                for edg in [edge rposts->:HasCreator:->] {
                    author_of[jid(edg.__jac__.source.archetype)] =
                        edg.__jac__.target.archetype;
                }
            }
        }
        out: list = [];
        for e in top10 {
            row = {"kind": e[0], "creationDate": e[1], "id": e[2]};
            if e[0] == "post" {
                row["content"] = e[3].content or e[3].imageFile;
                row["origPostId"] = e[2];
                row["origAuthorId"] = p.person_id;
            } else {
                cur = e[3];
                row["content"] = cur.content;
                rj = root_jid.get(jid(cur), "");
                # already loaded, above, in one call
                rp = root_of.get(rj);
                cur = rp if rp is not None else cur;
                if isinstance(cur, Post) {
                    row["origPostId"] = cur.post_id;
                    a = author_of.get(jid(cur));
                    if isinstance(a, Person) {
                        row["origAuthorId"] = a.person_id;
                    }
                }
            }
            out.append(row);
        }
        report {"messages": out};
    }
}

# burden: bench=snb feature=is3 arm=jac-lti
# burden: dbloc=16 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning: undirected KNOWS = manual union of both directions)
walker is3_friends {
    has person_jid: str = "";

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        out: list = [];
        for f in [p->:Knows:->[?:Person]] + [p<-:Knows:<-[?:Person]] {
            out.append({"personId": f.person_id, "firstName": f.firstName,
                        "lastName": f.lastName});
        }
        out.sort(key=lambda (d: dict) { d["personId"]; });
        report {"friends": out, "count": len(out)};
    }
}

# ---- complex reads --------------------------------------------------------

def _neighbors(p: Person) -> list {
    return [p->:Knows:->[?:Person]] + [p<-:Knows:<-[?:Person]];
}

# LEVEL-SYNC leveling (phase 4, 2026-08-14): tried, MEASURED, REJECTED as
# production for ic1/ic2/ic5 - kept as _lvl shadows below for the evidence.
# _neighbors() called per-node inside a BFS loop issues one round trip PER
# NODE VISITED (the chain-compile audit found ic1=16527, ic2=3467,
# ic5=378562 statements/request at SF1 scale on the per-node form).
# Batching the hop over the WHOLE frontier list in one compiled reference
# (`[frontier ->:Knows:-> [?:Person]]`, frontier a list not a single node -
# jac accepts a list as the origin) cut that to ic1=22, ic2=20, ic5=592
# statements (99.8%+ fewer round trips) - BUT a warm-mirror latency A/B
# (x3 median, same person, back-to-back) showed the per-node form WINS on
# wall-clock on all three rungs anyway: ic1 38.5s(old) vs 48.7s(new), ic2
# 12.1s(old) vs 25.2s(new), ic5 40.2s(old) vs 43.1s(new). The compiler's
# batched IN-list queries don't compile to one fused statement at this
# volume (ic5's "4 batched hops" still produced 592 statements, evidence
# of internal chunking) and apparently don't get a plan that exploits the
# reduced round-trip count either - see the ic5 EXPLAIN ANALYZE note in
# PROGRESS.log (seq scan on the widest batched hop, no index hit despite
# fewer round trips). So: production stays per-node (below); this batching
# technique - hop batching in the engine, visited-set/dedup/ranking in
# app code, same class as the sqlalchemy arm's level-sync BFS - is proven
# CORRECT (byte-identical answers, correctness-gated) but not currently a
# latency win on this runtime/data volume. Thesis-relevant either way.
def _neighbors_batch(frontier: list) -> list {
    return [frontier->:Knows:->[?:Person]] + [frontier<-:Knows:<-[?:Person]];
}

# burden: bench=snb feature=ic1 arm=jac-lti
# burden: dbloc=24 notations=[jac] entity-reps=1 hand-tuning=0
# burden: bench=snb feature=ic1 arm=jaseci-pg-cte
# burden: dbloc=17 notations=[jac] entity-reps=1 hand-tuning=0
# (T7 removed the last restatement: the edge type, endpoint type and depth cap
#  are now the walker's OWN traversal syntax - a variable-length hop
#  `[start<-:Knows:*3:->[?:Person, firstName==self.first_name]]`. Item #24
#  already removed the trailing sufficiency limit: the compiler infers it from
#  the walker's distance-first sort + report slice.)
walker ic1_friends_by_name {
    has person_jid: str = "",
        first_name: str = "";

    can run with Root entry {
        start = jobj(self.person_jid, Person);
        found: list = [];
        # Every Person within 3 Knows hops whose firstName matches, with its
        # SHORTEST hop count. The walker writes the hop and the endpoint
        # predicate; the compiler lowers both into ONE recursive CTE joined to
        # Person's mirror, so what comes back is the ANSWER (tens) and not the
        # neighbourhood (9036 at SF1). Item #24: the sufficiency threshold
        # (stop once depth<=d already holds enough nearest matches) is
        # INFERRED from the walker's own sort+slice below - EffectPass proves
        # distance is the dominant key and reads the report's [:20].
        for (f, dist) in [start<-:Knows:*3:->[?:Person, firstName==self.first_name]] {
            found.append({"personId": f.person_id,
                          "lastName": f.lastName,
                          "distance": dist});
        }
        found.sort(key=lambda (d: dict) { (d["distance"], d["lastName"], d["personId"]); });
        report {"people": found[:20]};
    }
}

# burden: bench=snb feature=ic2 arm=jac-lti
# burden: dbloc=22 notations=[jac] entity-reps=1 hand-tuning=0
# burden: bench=snb feature=ic2 arm=jaseci-pg-cte (JAC_CTE_TRAVERSE=1)
# burden: dbloc=27 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning 1: the app hands a top-K builtin the edge type, the two message
#  archetypes with their tie-break field names, the sort field, the bound and
#  the limit -- the ORDER BY / LIMIT the walker already spells out as a
#  sort+slice, restated for the engine. Same class of restatement as ic1's.
#  Item #23 removed what used to be hand-tuning 2 here: the denormalised
#  creator_jid field on Post/Comment, its by-hand maintenance on every
#  message-create path, its bulk-load backfill and its hand-built index are
#  now grown and trigger-maintained by the runtime.)
walker ic2_friend_messages {
    has person_jid: str = "",
        max_date: int = 0;

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        # ONE statement for the rung: the friends' Posts+Comments, date
        # bound applied, ordered (creationDate DESC, id ASC) and cut to 20
        # against the Post/Comment mirrors, returning 20 jids. The plain-hop
        # form instead loads EVERY message of every friend (17876 objects
        # at SF1) to keep 20. (creationDate DESC, id ASC) IS the
        # sort(key=(-creationDate, id)) the walker spells out; post_id and
        # comment_id are disjoint id spaces in SNB, so no cross-type tie can
        # reach the stable-sort fallback SQL has no way to reproduce.
        top = [];
        for mid in jtopk([jid(f) for f in _neighbors(p)], "HasCreator",
                         [(Post, "post_id"), (Comment, "comment_id")],
                         "creationDate", self.max_date, 20) {
            m = jobj(mid);
            if m is not None {
                top.append(m);
            }
        }
        # author identity is not a scalar on the message (no denormalised
        # creator id), so it needs its own hop - one batched edge query
        # over the 20 survivors, the ic2_lvl technique below.
        author_of: dict = {};
        if top {
            for edg in [edge top->:HasCreator:->] {
                author_of[jid(edg.__jac__.source.archetype)] =
                    edg.__jac__.target.archetype;
            }
        }
        out2: list = [];
        for m in top {
            a = author_of.get(jid(m));
            is_post = isinstance(m, Post);
            out2.append({
                "id": m.post_id if is_post else m.comment_id,
                "creationDate": m.creationDate,
                "content": (m.content or m.imageFile) if is_post else m.content,
                "authorId": a.person_id if a else None,
                "authorFirst": a.firstName if a else None,
                "authorLast": a.lastName if a else None
            });
        }
        report {"messages": out2};
    }
}

# burden: bench=snb feature=ic5 arm=jac-lti
# burden: dbloc=24 notations=[jac] entity-reps=1 hand-tuning=0
walker ic5_new_forums {
    has person_jid: str = "",
        min_date: int = 0;

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        # forum jid -> set of joined-friend jids (joinDate predicate on edge)
        joined: dict = {};
        forums: dict = {};
        for f in _neighbors(p) {
            fj = jid(f);
            for fo in [f<-:HasMember:joinDate > self.min_date:<-[?:Forum]] {
                foj = jid(fo);
                forums[foj] = fo;
                if foj not in joined {
                    joined[foj] = set();
                }
                joined[foj].add(fj);
            }
        }
        rows: list = [];
        for (foj, fo) in forums.items() {
            cnt = 0;
            for post in [fo->:ContainerOf:->[?:Post]] {
                creators = [post->:HasCreator:->[?:Person]];
                if creators and jid(creators[0]) in joined[foj] {
                    cnt += 1;
                }
            }
            rows.append({"forumId": fo.forum_id, "title": fo.title,
                         "postCount": cnt});
        }
        rows.sort(key=lambda (d: dict) { (-d["postCount"], d["forumId"]); });
        report {"forums": rows[:20]};
    }
}

# ---- LEVEL-SYNC SHADOWS (phase 4, 2026-08-14): batched-frontier form,
# correctness-gated identical to the walkers above, but measurably SLOWER
# on warm-mirror latency at SF1 scale (see the note above _neighbors_batch)
# - kept as evidence, not wired to production. ------------------------

# burden: bench=snb feature=ic1 arm=jaseci-pg-lvl (shadow, not production)
# burden: dbloc=28 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning: level-synchronous BFS - batch hop per frontier LEVEL instead
#  of per node, dedup/distance-tracking/ranking in python; see _neighbors_batch)
walker ic1_lvl {
    has person_jid: str = "",
        first_name: str = "";

    can run with Root entry {
        start = jobj(self.person_jid, Person);
        seen: set = {jid(start)};
        frontier: list = [start];
        found: list = [];
        for dist in range(1, 4) {
            nxt = _neighbors_batch(frontier);
            fresh: list = [];
            for n in nxt {
                nj = jid(n);
                if nj not in seen {
                    seen.add(nj);
                    fresh.append(n);
                    if n.firstName == self.first_name {
                        found.append({"personId": n.person_id,
                                      "lastName": n.lastName,
                                      "distance": dist});
                    }
                }
            }
            frontier = fresh;
            if not frontier {
                break;
            }
        }
        found.sort(key=lambda (d: dict) { (d["distance"], d["lastName"], d["personId"]); });
        report {"people": found[:20]};
    }
}

# burden: bench=snb feature=ic2 arm=jaseci-pg-lvl (shadow, not production)
# burden: dbloc=34 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning: ONE batched message fetch over the whole friend list instead
#  of a per-friend loop; author identity for the fetched Post/Comment isn't
#  a scalar field on the message [jac has no denormalized creator_id like
#  the sqla arm's FK column], so it needs its OWN hop - resolved via
#  `[edge <nodes> ->:HasCreator:->]` (batched edge-object query) which
#  pairs each edge's .__jac__.source/.target, done ONLY for the final
#  top-20 survivors [not all fetched messages] to keep it O(1) not O(friends))
walker ic2_lvl {
    has person_jid: str = "",
        max_date: int = 0;

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        friends = _neighbors(p);
        posts = [friends<-:HasCreator:<-[?:Post]];
        comments = [friends<-:HasCreator:<-[?:Comment]];
        msgs: list = [];
        for m in posts {
            if m.creationDate <= self.max_date {
                msgs.append([m.creationDate, m.post_id, m.content or m.imageFile, m]);
            }
        }
        for m in comments {
            if m.creationDate <= self.max_date {
                msgs.append([m.creationDate, m.comment_id, m.content, m]);
            }
        }
        msgs.sort(key=lambda (e: list) { (-e[0], e[1]); });
        top = msgs[:20];

        author_of: dict = {};
        top_nodes = [e[3] for e in top];
        if top_nodes {
            for edg in [edge top_nodes->:HasCreator:->] {
                author_of[jid(edg.__jac__.source.archetype)] = edg.__jac__.target.archetype;
            }
        }
        out: list = [];
        for e in top {
            a = author_of.get(jid(e[3]));
            out.append({"id": e[1], "creationDate": e[0], "content": e[2],
                        "authorId": a.person_id if a else None,
                        "authorFirst": a.firstName if a else None,
                        "authorLast": a.lastName if a else None});
        }
        report {"messages": out};
    }
}

# burden: bench=snb feature=ic5 arm=jaseci-pg-lvl (shadow, not production)
# burden: dbloc=46 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning: the 378562-stmt rung. Original was a QUADRUPLE-nested
#  per-node loop (friends x their-forums x forum-posts x post-creator).
#  Rewritten to 4 batched hops total regardless of fan-out: friend hop,
#  batched membership-edge pairing (forum<->friend), batched ContainerOf
#  edge pairing (forum<->post), batched HasCreator edge pairing
#  (post<->creator) - counting/grouping done in python from the 3
#  edge-pair dicts, same "hop batching in engine, set logic in app code"
#  technique as ic1/ic2 above)
walker ic5_lvl {
    has person_jid: str = "",
        min_date: int = 0;

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        friends = _neighbors(p);

        # batch 1: every (forum, friend) membership pair joined after min_date
        joined: dict = {};   # forum_jid -> set of friend jids
        forums: dict = {};   # forum_jid -> Forum archetype
        if friends {
            for edg in [edge friends<-:HasMember:joinDate > self.min_date:<-] {
                fo = edg.__jac__.source.archetype;
                fr = edg.__jac__.target.archetype;
                foj = jid(fo);
                forums[foj] = fo;
                if foj not in joined {
                    joined[foj] = set();
                }
                joined[foj].add(jid(fr));
            }
        }

        # batch 2: every (forum, post) pair for the qualifying forums
        posts_by_forum: dict = {};   # forum_jid -> list[Post]
        all_forums = list(forums.values());
        if all_forums {
            for edg in [edge all_forums->:ContainerOf:->] {
                fo = edg.__jac__.source.archetype;
                post = edg.__jac__.target.archetype;
                foj = jid(fo);
                posts_by_forum.setdefault(foj, []).append(post);
            }
        }

        # batch 3: creator of every post found above, in one shot
        all_posts = [post for plist in posts_by_forum.values() for post in plist];
        post_creator: dict = {};   # post_jid -> creator_jid
        if all_posts {
            for edg in [edge all_posts->:HasCreator:->] {
                post_creator[jid(edg.__jac__.source.archetype)] = jid(edg.__jac__.target.archetype);
            }
        }

        rows: list = [];
        for (foj, fo) in forums.items() {
            cnt = 0;
            for post in posts_by_forum.get(foj, []) {
                creator_jid = post_creator.get(jid(post));
                if creator_jid and creator_jid in joined[foj] {
                    cnt += 1;
                }
            }
            rows.append({"forumId": fo.forum_id, "title": fo.title,
                         "postCount": cnt});
        }
        rows.sort(key=lambda (d: dict) { (-d["postCount"], d["forumId"]); });
        report {"forums": rows[:20]};
    }
}

# burden: bench=snb feature=ic13 arm=jac-lti
# burden: dbloc=20 notations=[jac] entity-reps=1 hand-tuning=0
# burden: bench=snb feature=ic13 arm=jaseci-pg-cte
# burden: dbloc=4 notations=[jac] entity-reps=1 hand-tuning=0
# (T7: the traversal is now the walker's OWN syntax - a variable-length hop
#  `[a<-:Knows:*6:->[?:Person, person_id==b.person_id]]`. Nothing about the
#  engine is restated: the compiler lowers the hop to one recursive CTE,
#  pushes the endpoint predicate into it, and infers the sufficiency
#  threshold (limit=1) from `hits[0]` behind the emptiness test (#24,
#  single-element shape). The hand-written BFS arm no longer exists.)
walker ic13_shortest_path {
    has person1_jid: str = "",
        person2_jid: str = "";

    can run with Root entry {
        a = jobj(self.person1_jid, Person);
        b = jobj(self.person2_jid, Person);
        if self.person1_jid == self.person2_jid {
            report {"length": 0};
            return;
        }
        # b's own row out of the <=6-hop Knows closure from a: the walker
        # writes the hop, the compiler lowers it to ONE recursive CTE and
        # pushes the endpoint predicate in, so the walk stops at b's distance.
        # (node, min depth) pairs; empty == not reached within 6.
        hits = [a<-:Knows:*6:->[?:Person, person_id==b.person_id]];
        report {"length": int(hits[0][1]) if hits else -1};
    }
}

# ---- depth-sweep workloads (session0831 harness build; THE slope figure) ---

# burden: bench=snb feature=ic1_depth arm=jac-lti
# burden: dbloc=24 notations=[jac] entity-reps=1 hand-tuning=0
# ic1 with the depth cap a runtime parameter: the latency-vs-depth slope per
# engine is the figure. Naive arm = per-hop BFS (depth more hops = more round
# trips); CTE arm = jclosure with max_depth=self.depth (ONE recursive CTE
# regardless of depth - the structural claim under test).
walker ic1_depth {
    has person_jid: str = "",
        first_name: str = "",
        depth: int = 3;

    can run with Root entry {
        start = jobj(self.person_jid, Person);
        found: list = [];
        for (f, dist) in [start<-:Knows:*self.depth:->[?:Person, firstName==self.first_name]] {
            found.append({"personId": f.person_id,
                          "lastName": f.lastName,
                          "distance": dist});
        }
        found.sort(key=lambda (d: dict) { (d["distance"], d["lastName"], d["personId"]); });
        report {"people": found[:20]};
    }
}

# burden: bench=snb feature=pymk arm=jac-lti
# burden: dbloc=40 notations=[jac] entity-reps=1 hand-tuning=0
# People-You-May-Know at depth d: candidates at min-distance exactly d,
# scored by how many DISTINCT distance-(d-1) connections they touch
# (d=2: classic mutual-friend count), top 20 by (mutual DESC, personId ASC).
# Path-count aggregation is procedural - no builtin expresses it - so the
# naive arm is the full per-node BFS; the relational arms answer it with a
# join-chain + GROUP BY. That asymmetry is part of what the figure shows.
# burden: bench=snb feature=pymk arm=jaseci-pg-cte
# burden: dbloc=15 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning 1: the depth-d rings are now the walker's own variable-length
#  hop (T7), but jadj_pairs still takes the edge/node type as strings - ONE
#  adjacency-pairs statement over the WHOLE ring-(d-1) for its (connector,
#  candidate) pairs, the same symmetric pairs table the postgres arm reads -
#  ids only, no object hydration until the final candidate batch load.
#  The batched node reference
#  `[ring->:Knows:->]` dedups across origins and loses the pairing; the
#  edge-object form `[edge ring->:Knows:->]` keeps it but materializes every
#  edge and both endpoints (1.3-1.6x SLOWER at SF1, session0901/port_jclosure)
#  and the compiler does not yet lower that form to the pairs statement -
#  session0901/opt_ladder/T2/DESIGN.md section 4.)
walker pymk {
    has person_jid: str = "",
        depth: int = 2;

    can run with Root entry {
        start = jobj(self.person_jid, Person);
        rows: list = [];
        if self.depth <= 1 {
            # degenerate rung, kept for slope calibration: every friend is a
            # "candidate" with exactly one connector (me)
            for f in _neighbors(start) {
                rows.append({"personId": f.person_id,
                             "firstName": f.firstName,
                             "lastName": f.lastName, "mutual": 1});
            }
        } else {
            # The whole <=d closure as (node, min depth) pairs from ONE
            # variable-length hop the walker writes itself; rings are read off
            # the depth. Then ONE adjacency-pairs statement lists the
            # (connector, neighbour) id pairs for the WHOLE ring-(d-1) at once
            # - ids only, no node objects; a neighbour at depth d is a
            # candidate and the connector it came back paired with is one of
            # its DISTINCT connectors, identical to a visited-set BFS's
            # mutual[cj] set, because BFS assigns each node its shortest hop
            # count and so does MIN(depth). Candidates are hydrated once, in
            # one batch, at the end.
            reach = [start<-:Knows:*self.depth:->[?:Person]];
            dist_of: dict = {jid(n): d for (n, d) in reach};
            ring: list = [j for (j, d) in dist_of.items() if d == self.depth - 1];
            mutual: dict = {};
            for (nj, cj) in jadj_pairs(ring, "Knows", Person) {
                if dist_of.get(cj, -1) == self.depth {
                    if cj not in mutual {
                        mutual[cj] = set();
                    }
                    mutual[cj].add(nj);
                }
            }
            for c in jobj_many(list(mutual.keys())) {
                if isinstance(c, Person) {
                    rows.append({"personId": c.person_id,
                                 "firstName": c.firstName,
                                 "lastName": c.lastName,
                                 "mutual": len(mutual[jid(c)])});
                }
            }
        }
        rows.sort(key=lambda (d: dict) { (-d["mutual"], d["personId"]); });
        report {"people": rows[:20]};
    }
}

# ---- updates --------------------------------------------------------------

# burden: bench=snb feature=add_post arm=jac-lti
# burden: dbloc=16 notations=[jac] entity-reps=1 hand-tuning=0
walker add_post {
    has person_jid: str = "",
        forum_jid: str = "",
        post_id: int = 0,
        content: str = "",
        length: int = 0;

    can run with Root entry {
        p = jobj(self.person_jid, Person);
        f = jobj(self.forum_jid, Forum);
        new = here ++> Post(
            post_id=self.post_id, creationDate=_now_ms(),
            content=self.content, length=self.length
        );
        new +>:HasCreator():+> p;
        f +>:ContainerOf():+> new;
        report {"success": True, "post_jid": jid(new)};
    }
}

# burden: bench=snb feature=add_friendship arm=jac-lti
# burden: dbloc=12 notations=[jac] entity-reps=1 hand-tuning=0
walker add_friendship {
    has person1_jid: str = "",
        person2_jid: str = "";

    can run with Root entry {
        a = jobj(self.person1_jid, Person);
        b = jobj(self.person2_jid, Person);
        if b not in [a->:Knows:->[?:Person]] + [a<-:Knows:<-[?:Person]] {
            a +>:Knows(creationDate=_now_ms()):+> b;
        }
        report {"success": True};
    }
}

"""Bulk seed walkers for the TPC-C jac arm.

Chunked server-side imports: one HTTP call spawns a whole chunk of nodes
in-process (vs littleX's per-entity HTTP seeding). Two accounts hold the
graph: tpcc_catalog owns Item nodes (granted WRITE so warehouse-root walkers
can read prices and hang Stock -:Of:-> edges cross-root), tpcc_w1 owns the
operational tree.

# burden: bench=tpcc feature=loader arm=jac-lti
# burden: dbloc=68 notations=[jac] entity-reps=1 hand-tuning=1
# (hand-tuning: chunked import walkers instead of per-entity seeding -
#  bulk-load path built for load speed, mirrors the pg COPY choice)
"""

import from typing { cast }
import from app { Warehouse, District, Customer, History, Item, Stock, Order, OrderLine, Placed, Of }

# catalog account: items under its root, world-writable for cross-root
# price reads + stock edges (littleX tweet-grant precedent)
walker:protect seed_items {
    has rows: list[dict] = [];

    can run with Root entry {
        jids: list = [];
        for r in self.rows {
            i = here ++> Item(
                i_id=r["i_id"], i_im_id=r["i_im_id"], i_name=r["i_name"],
                i_price=r["i_price"], i_data=r["i_data"]
            );
            grant(i, level="WRITE");
            jids.append(jid(i));
        }
        report jids;
    }
}

walker:protect seed_warehouse {
    has row: dict = {};

    can run with Root entry {
        w = here ++> Warehouse(
            w_id=self.row["w_id"], w_name=self.row["w_name"],
            w_street_1=self.row["w_street_1"], w_street_2=self.row["w_street_2"],
            w_city=self.row["w_city"], w_state=self.row["w_state"],
            w_zip=self.row["w_zip"], w_tax=self.row["w_tax"],
            w_ytd=self.row["w_ytd"]
        );
        report jid(w);
    }
}

walker:protect seed_districts {
    has warehouse_id: str = "",
        rows: list[dict] = [];

    can run with Root entry {
        w = jobj(self.warehouse_id);
        jids: list = [];
        if isinstance(w, Warehouse) {
            for r in self.rows {
                d = w ++> District(
                    d_id=r["d_id"], d_name=r["d_name"],
                    d_street_1=r["d_street_1"], d_street_2=r["d_street_2"],
                    d_city=r["d_city"], d_state=r["d_state"], d_zip=r["d_zip"],
                    d_tax=r["d_tax"], d_ytd=r["d_ytd"],
                    d_next_o_id=r["d_next_o_id"]
                );
                jids.append(jid(d));
            }
        }
        report jids;
    }
}

walker:protect seed_customers {
    has district_id: str = "",
        rows: list[dict] = [];

    can run with Root entry {
        d = jobj(self.district_id);
        jids: list = [];
        if isinstance(d, District) {
            for r in self.rows {
                c = d ++> Customer(
                    c_id=r["c_id"], c_first=r["c_first"], c_middle=r["c_middle"],
                    c_last=r["c_last"], c_street_1=r["c_street_1"],
                    c_street_2=r["c_street_2"], c_city=r["c_city"],
                    c_state=r["c_state"], c_zip=r["c_zip"], c_phone=r["c_phone"],
                    c_since=r["c_since"], c_credit=r["c_credit"],
                    c_credit_lim=r["c_credit_lim"], c_discount=r["c_discount"],
                    c_balance=r["c_balance"], c_ytd_payment=r["c_ytd_payment"],
                    c_payment_cnt=r["c_payment_cnt"],
                    c_delivery_cnt=r["c_delivery_cnt"], c_data=r["c_data"]
                );
                c ++> History(
                    h_d_id=r["c_d_id"], h_w_id=r["c_w_id"], h_date=r["c_since"],
                    h_amount=10.0, h_data="seed"
                );
                jids.append(jid(c));
            }
        }
        report jids;
    }
}

walker:protect seed_stock {
    has warehouse_id: str = "",
        rows: list[dict] = [];

    can run with Root entry {
        w = jobj(self.warehouse_id);
        jids: list = [];
        if isinstance(w, Warehouse) {
            for r in self.rows {
                s = cast(Stock, w ++> Stock(
                    s_i_id=r["s_i_id"], s_quantity=r["s_quantity"],
                    s_dist=r["s_dist"], s_ytd=r["s_ytd"],
                    s_order_cnt=r["s_order_cnt"],
                    s_remote_cnt=r["s_remote_cnt"], s_data=r["s_data"]
                ));
                item = jobj(r["item_id"]);
                if isinstance(item, Item) {
                    s +>:Of():+> item;
                }
                jids.append(jid(s));
            }
        }
        report jids;
    }
}

walker:protect seed_orders {
    has rows: list[dict] = [];

    can run with Root entry {
        n = 0;
        for r in self.rows {
            c = jobj(r["customer_id"]);
            if isinstance(c, Customer) {
                o = cast(Order, c +>:Placed():+> Order(
                    o_id=r["o_id"], o_c_id=r["o_c_id"], o_d_id=r["o_d_id"],
                    o_entry_d=r["o_entry_d"],
                    o_carrier_id=r["o_carrier_id"] or 0,
                    o_ol_cnt=r["o_ol_cnt"], o_all_local=r["o_all_local"],
                    new_order=r["new_order"]
                ));
                for ln in r["lines"] {
                    o ++> OrderLine(
                        ol_number=ln["ol_number"], ol_i_id=ln["ol_i_id"],
                        ol_supply_w_id=ln["ol_supply_w_id"],
                        ol_delivery_d=ln["ol_delivery_d"] or "",
                        ol_quantity=ln["ol_quantity"],
                        ol_amount=ln["ol_amount"],
                        ol_dist_info=ln["ol_dist_info"]
                    );
                }
                n = n + 1;
            }
        }
        report n;
    }
}

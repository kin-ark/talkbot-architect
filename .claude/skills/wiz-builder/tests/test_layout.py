from wizbuilder.layout import assign_positions


def _node(is_default=False):
    return {"data": {"is_default": 1 if is_default else 0}}


def _edge(dst):
    return {"target": {"type": 1, "uuid": dst}}


def test_linear_ranks_top_increases():
    details = {"e": _node(True), "a": _node(), "b": _node(), "x": _node()}
    routes = {"e": {"p1": _edge("a")}, "a": {"p2": _edge("b")}, "b": {"p3": _edge("x")}, "x": {}}
    assign_positions(details, routes)
    t = {k: details[k]["data"]["top"] for k in details}
    assert t["e"] < t["a"] < t["b"] < t["x"]
    for k in details:
        assert isinstance(details[k]["data"]["top"], int)
        assert isinstance(details[k]["data"]["left"], int)


def test_branches_share_rank_distinct_left():
    details = {"e": _node(True), "a": _node(), "b": _node(), "c": _node()}
    routes = {
        "e": {"p1": _edge("a"), "p2": _edge("b"), "p3": _edge("c")},
        "a": {},
        "b": {},
        "c": {},
    }
    assign_positions(details, routes)
    tops = {details[k]["data"]["top"] for k in ("a", "b", "c")}
    lefts = {details[k]["data"]["left"] for k in ("a", "b", "c")}
    assert len(tops) == 1        # same rank
    assert len(lefts) == 3       # distinct columns


def test_no_two_nodes_share_position():
    details = {c: _node(c == "e") for c in "eabcdef"}
    routes = {"e": {"p": _edge("a")}, "a": {"p1": _edge("b"), "p2": _edge("c")},
              "b": {"p": _edge("d")}, "c": {"p": _edge("e2")}, "d": {}, "f": {}}
    assign_positions(details, routes)
    seen = set()
    for k in details:
        pos = (details[k]["data"]["top"], details[k]["data"]["left"])
        assert pos not in seen, f"{k} collides at {pos}"
        seen.add(pos)


def test_orphan_gets_placed_not_at_entry():
    details = {"e": _node(True), "a": _node(), "orphan": _node()}
    routes = {"e": {"p": _edge("a")}, "a": {}, "orphan": {}}
    assign_positions(details, routes)
    epos = (details["e"]["data"]["top"], details["e"]["data"]["left"])
    opos = (details["orphan"]["data"]["top"], details["orphan"]["data"]["left"])
    assert opos != epos


def test_cycle_terminates_and_positions_all():
    details = {"e": _node(True), "a": _node(), "b": _node()}
    routes = {"e": {"p": _edge("a")}, "a": {"p": _edge("b")}, "b": {"p": _edge("a")}}  # b→a cycle
    assign_positions(details, routes)
    assert all("top" in details[k]["data"] for k in details)


def test_deterministic():
    def build():
        d = {"e": _node(True), "a": _node(), "b": _node()}
        r = {"e": {"p1": _edge("a"), "p2": _edge("b")}, "a": {}, "b": {}}
        assign_positions(d, r)
        return {k: (d[k]["data"]["top"], d[k]["data"]["left"]) for k in d}
    assert build() == build()


def test_cross_component_target_ignored():
    # edge to a uuid not in details (goto another component) must not crash
    details = {"e": _node(True), "a": _node()}
    routes = {"e": {"p1": _edge("a"), "p2": _edge("EXTERNAL")}, "a": {}}
    assign_positions(details, routes)
    assert "top" in details["a"]["data"]


def test_writes_canvas_and_data_position():
    details = {"e": _node(True), "a": _node(), "b": _node()}
    routes = {"e": {"p1": _edge("a"), "p2": _edge("b")}, "a": {}, "b": {}}
    assign_positions(details, routes)
    for k in details:
        dp = details[k]["data"]["position"]
        cp = details[k]["canvas"]["position"]
        assert dp == cp                                  # data + canvas mirror
        assert dp == {"x": details[k]["data"]["left"], "y": details[k]["data"]["top"]}
    # distinct canvas positions (the field WIZ renders from) — no stack
    pos = {tuple(details[k]["canvas"]["position"].values()) for k in details}
    assert len(pos) == len(details)

from wizbuilder.noderender import EdgeSpec, NodeSpec, render_component_nodes


class _Minter:
    manifest_hash = "test"

    def uuid(self, seed: str) -> str:
        return f"uuid-{seed}"

    def int_id(self, seed: str) -> int:
        return abs(hash(seed)) % (2**31)


_BII = {
    "Positive": 1, "Negative": 2, "Reject": 3, "Unclassified": 4, "No answer": 5,
    "PaidCash": 101, "PaidTransfer": 102,
}


def _render(spec, edges):
    return render_component_nodes(
        [spec, NodeSpec(id="end", prompt="Bye", type="exit")],
        [EdgeSpec(src=spec.id, branch=b, dst="end") for b in edges],
        canvas_index=0, comp_uuid="C", speech_id=7, branch_intent_ids=_BII,
        kb_ids=[], node_language="3", minter=_Minter(),
    )


def test_custom_branch_mints_port_and_bound_intent():
    spec = NodeSpec(id="ask", prompt="Paid?", type="talk",
                    config={"branch_intents": {"Paid": ["PaidCash", "PaidTransfer"]}})
    r = _render(spec, ["Paid", "Unclassified"])
    talk = r.details["uuid-node:0:ask"]
    port_names = [p["name"] for p in talk["canvas"]["ports"]["items"]]
    assert "Paid" in port_names                       # custom port minted
    assert {"Positive", "Negative", "Unclassified"} <= set(port_names)  # system kept
    aci = {row["name"]: row for row in talk["data"]["all_client_intent"]}
    assert aci["Paid"]["intents"] == [{"intentId": "101"}, {"intentId": "102"}]
    assert aci["Paid"]["checked"] is True
    assert "id" in aci["Paid"]                         # custom row carries a port-uuid id


def test_no_custom_branches_still_three_system_ports():
    spec = NodeSpec(id="ask", prompt="Hi", type="talk")
    r = _render(spec, ["Positive", "Unclassified"])
    talk = r.details["uuid-node:0:ask"]
    port_names = [p["name"] for p in talk["canvas"]["ports"]["items"]]
    assert port_names == ["Positive", "Negative", "Unclassified"]   # unchanged shape
    names = [row["name"] for row in talk["data"]["all_client_intent"]]
    assert names == ["Positive", "Negative", "Reject", "Unclassified", "No answer"]

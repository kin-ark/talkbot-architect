from tools.registry import tool_specs


def _scaffold_spec():
    for spec in tool_specs():
        if spec.name == "scaffold_bot":
            return spec
    raise AssertionError("scaffold_bot not registered")


def test_scaffold_schema_declares_branch_intents():
    spec = _scaffold_spec()
    node_props = (spec.parameters["properties"]["canvases"]["items"]
                  ["properties"]["nodes"]["items"]["properties"])
    cfg_props = node_props["config"]["properties"]
    assert "branch_intents" in cfg_props
    assert cfg_props["branch_intents"]["type"] == "object"

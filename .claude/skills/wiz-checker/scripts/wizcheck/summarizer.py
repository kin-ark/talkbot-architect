from wizcheck.ir import WizFile


def build_summary_tree(wf: WizFile) -> dict:
    """Build a summary tree from wf.flow_model.

    Returns {"mainFlow": [...], "knowledgeBases": [...]}.
    mainFlow is a list of component trees; each component has "name" and
    "children" (the tree of FlowModelNodes rooted at entry_uuid / root_uuids).
    knowledgeBases mirrors wf.flow_model.knowledge_bases.

    Returns the empty shape if flow_model is None or has no components.
    """
    if wf.flow_model is None or not wf.flow_model.components:
        return {"mainFlow": [], "knowledgeBases": []}

    def _build_node_tree(comp, node_uuid: str, visited: set) -> dict:  # noqa: ANN001
        if node_uuid in visited:
            return {"name": f"[Cycle detected] {node_uuid}", "uuid": node_uuid,
                    "node_type": "unknown", "allowedKBs": [], "children": []}
        visited = visited | {node_uuid}  # immutable copy per branch

        node = comp.nodes.get(node_uuid)
        if node is None:
            return {"name": f"Unknown Node {node_uuid}", "uuid": node_uuid,
                    "node_type": "unknown", "allowedKBs": [], "children": []}

        node_data = {
            "name": node.label or node.text or "Talk Node",
            "uuid": node_uuid,
            "node_type": node.node_type,
            "allowedKBs": node.allowed_kbs,
            "children": [],
        }

        # Descend via same-component branch targets only
        for branch in node.branches:
            if branch.target_uuid is not None:
                child = _build_node_tree(comp, branch.target_uuid, visited)
                node_data["children"].append(child)

        return node_data

    main_flow = []

    for comp in wf.flow_model.components:
        comp_tree = {
            "name": comp.name,
            "children": [],
        }

        # Root traversal: prefer entry_uuid, fall back to root_uuids
        roots = comp.root_uuids if comp.root_uuids else (
            [comp.entry_uuid] if comp.entry_uuid else []
        )
        for r_uuid in roots:
            comp_tree["children"].append(_build_node_tree(comp, r_uuid, set()))

        main_flow.append(comp_tree)

    knowledge_bases = [
        {"knowledgeId": kb.knowledge_id, "title": kb.title}
        for kb in wf.flow_model.knowledge_bases
    ]

    return {"mainFlow": main_flow, "knowledgeBases": knowledge_bases}


def build_markdown_summary(wf: WizFile) -> str:
    tree = build_summary_tree(wf)
    if not tree or not tree.get("mainFlow"):
        return "No summary available"

    lines = []

    def _walk(node, depth):
        indent = "  " * depth
        node_type = f" [Type: {node['node_type']}]" if "node_type" in node else ""
        allowed_kbs = f" [KBs: {node['allowedKBs']}]" if node.get("allowedKBs") else ""
        lines.append(f"{indent}- {node.get('name', 'Unknown')}{node_type}{allowed_kbs}")
        for child in node.get("children", []):
            _walk(child, depth + 1)

    lines.append("- Talkbot Dialogue")
    for comp in tree.get("mainFlow", []):
        _walk(comp, 1)

    kbs = tree.get("knowledgeBases", [])
    if kbs:
        lines.append("- Knowledge Bases")
        for kb in kbs:
            lines.append(f"  - {kb['title']} (ID: {kb['knowledgeId']})")

    return "\n".join(lines)

from wizcheck.ir import WizFile
from collections import defaultdict
from uuid import UUID

def build_summary_tree(wf: WizFile) -> dict:
    if not hasattr(wf, 'components') or not wf.components:
        return {}

    root_node = {
        "name": "Talkbot Dialogue",
        "children": []
    }
    
    for comp_uuid, comp in wf.components.items():
        comp_name = comp.raw.get("componentName", f"Component {comp_uuid}")
        comp_tree = {
            "name": comp_name,
            "children": []
        }
        
        children_map = defaultdict(list)
        for node_uuid, node in comp.details.flow_nodes.items():
            if node.parent_uuid:
                children_map[node.parent_uuid].append(node)
                
        def build_node_tree(node_uuid: UUID, visited: set) -> dict:
            if node_uuid in visited:
                return {"name": f"[Cycle detected] {node_uuid}"}
            visited.add(node_uuid)
            
            node = comp.details.flow_nodes.get(node_uuid)
            if not node:
                return {"name": f"Unknown Node {node_uuid}"}
                
            node_data = {"name": node.label, "uuid": str(node_uuid)}
            children = children_map.get(node_uuid, [])
            if children:
                children.sort(key=lambda x: x.sort_index)
                node_data["children"] = [build_node_tree(c.uuid, visited.copy()) for c in children]
            return node_data

        for r_uuid in comp.details.root_uuids:
            comp_tree["children"].append(build_node_tree(r_uuid, set()))
            
        root_node["children"].append(comp_tree)
        
    return root_node

def build_markdown_summary(wf: WizFile) -> str:
    tree = build_summary_tree(wf)
    if not tree:
        return "No summary available"
        
    lines = []
    def _walk(node, depth):
        indent = "  " * depth
        lines.append(f"{indent}- {node.get('name', 'Unknown')}")
        for child in node.get("children", []):
            _walk(child, depth + 1)
            
    _walk(tree, 0)
    return "\n".join(lines)

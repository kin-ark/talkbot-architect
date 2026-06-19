from wizcheck.ir import WizFile
from collections import defaultdict
from uuid import UUID

def build_summary_tree(wf: WizFile) -> dict:
    if not hasattr(wf, 'components') or not wf.components:
        return {"mainFlow": [], "knowledgeBases": []}

    main_flow = []
    
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
                
            node_data = {
                "name": node.label, 
                "uuid": str(node_uuid),
                "node_type": comp.category,
                "allowedKBs": node.raw.get("data", {}).get("allow_jump_knowledges", [])
            }
            children = children_map.get(node_uuid, [])
            if children:
                children.sort(key=lambda x: x.sort_index)
                node_data["children"] = [build_node_tree(c.uuid, visited.copy()) for c in children]
            return node_data

        for r_uuid in comp.details.root_uuids:
            comp_tree["children"].append(build_node_tree(r_uuid, set()))
            
        main_flow.append(comp_tree)
        
    knowledge_bases = []
    if getattr(wf, 'knowledge_bases', None):
        for kb_id, kb in wf.knowledge_bases.items():
            knowledge_bases.append({
                "knowledgeId": kb.knowledge_id,
                "title": kb.title,
                "kdType": kb.kd_type,
                "intents": list(kb.intents)
            })
            
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

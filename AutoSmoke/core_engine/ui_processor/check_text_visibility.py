"""from AutoSmoke.path_utils import as_abs_pathI?""" import json def find_node_with_text(tree, target_text, path=""): """ I? """ 
 if not isinstance(tree, dict):
 return None payload = tree.get('payload', {}) text = payload.get('text', '')
 if text == target_text:
 return tree, path # ? children = tree.get('children', [])
 if isinstance(children, list):
 for i, child in enumerate(children):
 result = find_node_with_text(child, target_text, path + '.children[' + str(i) + ']')
 if result is not None:
 return result 
 return None def check_parent_visibility(tree, target_path): """ ? """ #  # ?
 pass def main(): # UI?
 with open(as_abs_path('reports/runtime_capture/ui_tree_20260611_120143.json'), 'r', encoding='utf-8') as f: ui_tree = json.load(f) #  target_texts = ["?, "?, "", "", "?]
 print("=" * 60)
 print("UI?)
 print("=" * 60)
 for target_text in target_texts:
 print(f"\n: '{target_text}'")
 result = find_node_with_text(ui_tree, target_text)
 if result is not None: node, path = result payload = node.get('payload', {}) visible = payload.get('visible', True) active = node.get('active', True)
 print(f" !")
 print(f" : {path}")
 print(f" visible: {visible}")
 print(f" active: {active}") #  # ath # ?
 else:
 print(f" ?)
 if __name__ == '__main__': main() 

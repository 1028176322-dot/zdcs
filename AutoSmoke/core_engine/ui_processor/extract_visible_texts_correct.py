"""from AutoSmoke.path_utils import as_abs_path??""" import json def is_node_visible(node, ui_tree): """ ? ? """ 
 if not isinstance(node, dict):
 return False payload = node.get('payload', {}) # ? visible = payload.get('visible', True) active = node.get('active', True)
 if not visible or not active:
 return False # ame node_name = payload.get('name', '') #  # I parent = find_parent_node(ui_tree, node_name)
 if parent is not None:
 return is_node_visible(parent, ui_tree)
 return True def find_parent_node(tree, target_name, parent=None): """ I """ 
 if not isinstance(tree, dict):
 return None payload = tree.get('payload', {}) name = payload.get('name', '')
 if name == target_name:
 return parent # ? children = tree.get('children', [])
 if isinstance(children, list):
 for child in children:
 result = find_parent_node(child, target_name, tree)
 if result is not None:
 return result 
 return None def extract_visible_texts_correct(ui_tree): """ ? """ visible_texts = []
 def traverse(node):
 if not isinstance(node, dict):
 return # ?
 if not is_node_visible(node, ui_tree):
 return #  payload = node.get('payload', {}) text = payload.get('text', '').strip()
 if text and any('\u4e00' <= c <= '\u9fff' for c in text): visible_texts.append(text) # ? children = node.get('children', [])
 if isinstance(children, list):
 for child in children: traverse(child) traverse(ui_tree)
 return visible_texts def main(): # UI?
 with open(as_abs_path('reports/runtime_capture/ui_tree_20260611_120143.json'), 'r', encoding='utf-8') as f: ui_tree = json.load(f)
 print("=" * 60)
 print("")
 print("=" * 60) #  visible_texts = extract_visible_texts_correct(ui_tree) # ? unique_texts = list(set(visible_texts)) unique_texts.sort()
 print(f"\n {len(unique_texts)} n")
 for i, text in enumerate(unique_texts, 1):
 print(f"{i}. {text}") # ? output_file = as_abs_path('reports/runtime_capture/visible_chinese_texts_corrected.txt')
 with open(output_file, 'w', encoding='utf-8') as f: f.write("\n") f.write("=" * 60 + "\n\n")
 for i, text in enumerate(unique_texts, 1): f.write(f"{i}. {text}\n")
 print(f"\n?: {output_file}")
 return output_file if __name__ == '__main__': main() 

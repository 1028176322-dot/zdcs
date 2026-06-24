"""from AutoSmoke.path_utils import as_abs_path"" ?"?""" import json def find_text_node_and_its_region(ui_tree, target_text=""): """ UI? """ target_node = None target_parent = None target_region = None 
 def traverse(obj, parent=None, depth=0): nonlocal target_node, target_parent, target_region 
 if not isinstance(obj, dict):
 return payload = obj.get('payload', {}) text = payload.get('text', '') #  
 if target_text in text: target_node = obj target_parent = parent # "" 
 if isinstance(parent, dict): target_region = parent.get('children', [])
 return #  children = obj.get('children', [])
 if isinstance(children, list):
 for child in children: traverse(child, obj, depth + 1)
 if target_node is not None:
 return traverse(ui_tree)
 return target_node, target_parent, target_region def extract_clickable_from_region(region): """  """ clickable_elements = []
 if not isinstance(region, list):
 return clickable_elements 
 for node in region:
 if not isinstance(node, dict):
 continue payload = node.get('payload', {}) name = payload.get('name', '') visible = payload.get('visible', True) clickable = payload.get('clickable', False) # ?
 if clickable and visible and name: # ? text = extract_text_from_node(node) clickable_elements.append({ 'name': name, 'text': text, 'visible': visible, 'clickable': clickable }) # ? children = node.get('children', [])
 if isinstance(children, list): clickable_elements.extend(extract_clickable_from_region(children))
 return clickable_elements def extract_text_from_node(node): """ ? """ 
 if not isinstance(node, dict):
 return '(?' payload = node.get('payload', {}) text = payload.get('text', '').strip() #  
 if text:
 return text # ? children = node.get('children', [])
 if isinstance(children, list):
 for child in children:
 result = extract_text_from_node(child)
 if result!= '(?':
 return result 
 return '(?' def main(): # UI?
 with open(as_abs_path('reports/runtime_capture/ui_tree_20260611_121626.json'), 'r', encoding='utf-8') as f: ui_tree = json.load(f)
 print("=" * 60)
 print("''")
 print("=" * 60) # "" target_node, target_parent, target_region = find_text_node_and_its_region(ui_tree)
 if target_node is None:
 print("\n??'")
 return 
 print(f"\n?''") # ?
 if target_region is None:
 print("\n??)
 return clickable_elements = extract_clickable_from_region(target_region)
 print(f"\n? {len(clickable_elements)} n") #  
 for i, elem in enumerate(clickable_elements, 1):
 print(f"{i}. {elem['name']}")
 print(f" : {elem['text'][:50]}")
 print() # ? timestamp = '20260611_121626' output_file = as_abs_path('reports/runtime_capture/activity_page_elements_{timestamp}.json')
 with open(output_file, 'w', encoding='utf-8') as f: json.dump(clickable_elements, f, ensure_ascii=False, indent=2)
 print(f"?? {output_file}") # HTML html_content = f"""<!DOCTYPE html> <html> <head> <meta charset="utf-8"> <title> - ?/title> <style> body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }} .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }} h1 {{ color: #333; }} .info {{ background: #e8f5e9; padding: 10px; border-radius: 4px; margin-bottom: 20px; }} .element-list {{ list-style: none; padding: 0; }} .element-item {{ padding: 15px; margin: 10px 0; background: #fafafa; border-left: 4px solid #4caf50; border-radius: 4px; }} .element-name {{ font-weight: bold; color: #333; font-size: 1.1em; }} .element-text {{ color: #666; margin-top: 5px; margin-left: 10px; }} </style> </head> <body> <div class="container"> <h1>  - ?/h1> <div class="info"> <p><strong>?/strong>UIActivityMain?/p> <p><strong>?/strong> > </p> <p><strong></strong>{len(clickable_elements)} ?/p> <p><strong>?/strong>?/p> </div> <ul class="element-list"> """ 
 for i, elem in enumerate(clickable_elements, 1): html_content += f""" <li class="element-item"> <div class="element-name">{i}. {elem['name']}</div> <div class="element-text"> : {elem['text'][:100]}</div> </li> """ html_content += """ </ul> </div> </body> </html>""" html_file = as_abs_path('reports/runtime_capture/activity_page_elements_{timestamp}.html')
 with open(html_file, 'w', encoding='utf-8') as f: f.write(html_content)
 print(f"?HTML? {html_file}")
 return html_file if __name__ == '__main__': main() 


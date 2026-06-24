"""from AutoSmoke.path_utils import as_abs_pathClickContent?lickContent?""" import json def find_clickcontent_with_siblings(ui_tree): """ lickContent? """ results = []
 def find_parent_and_process(obj, parent=None, depth=0):
 if not isinstance(obj, dict):
 return payload = obj.get('payload', {}) name = payload.get('name', '') # lickContent 
 if 'ClickContent' in name: visible = payload.get('visible', True)
 if visible: # ? sibling_texts = []
 if isinstance(parent, dict): sibling_texts = extract_texts_from_siblings(parent, obj) results.append({ 'name': name, 'sibling_texts': sibling_texts, 'primary_text': sibling_texts[0] if sibling_texts else '(?' }) #  children = obj.get('children', [])
 if isinstance(children, list):
 for child in children: find_parent_and_process(child, obj, depth + 1) find_parent_and_process(ui_tree)
 return results def extract_texts_from_siblings(parent_node, target_node): """ ? """ texts = []
 if not isinstance(parent_node, dict):
 return texts children = parent_node.get('children', [])
 if not isinstance(children, list):
 return texts #  
 for sibling in children:
 if sibling is target_node:
 continue #  # ? extract_texts_from_node(sibling, texts)
 return texts def extract_texts_from_node(node, texts): """ ? """ 
 if not isinstance(node, dict):
 return payload = node.get('payload', {}) text = payload.get('text', '').strip() # ?
 if text and any('\u4e00' <= c <= '\u9fff' for c in text):
 if text not in texts: #  texts.append(text) # ? children = node.get('children', [])
 if isinstance(children, list):
 for child in children: extract_texts_from_node(child, texts)
 def main(): # UI?
 with open(as_abs_path('reports/runtime_capture/ui_tree_20260611_121626.json'), 'r', encoding='utf-8') as f: ui_tree = json.load(f)
 print("=" * 60)
 print("ClickContent")
 print("=" * 60) # lickContent? results = find_clickcontent_with_siblings(ui_tree)
 print(f"\n {len(results)} ClickContentn")
 for i, result in enumerate(results, 1):
 print(f"{i}. {result['name']}")
 print(f" : {result['primary_text']}")
 if len(result['sibling_texts']) > 1:
 print(f" : {', '.join(result['sibling_texts'][1:])}")
 print() # ? timestamp = '20260611_121626' output_file = as_abs_path('reports/runtime_capture/clickcontent_with_sibling_texts_{timestamp}.json')
 with open(output_file, 'w', encoding='utf-8') as f: json.dump(results, f, ensure_ascii=False, indent=2)
 print(f"?? {output_file}") # HTML html_content = f"""<!DOCTYPE html> <html> <head> <meta charset="utf-8"> <title> - ?/title> <style> body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }} .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }} h1 {{ color: #333; }} .info {{ background: #e8f5e9; padding: 10px; border-radius: 4px; margin-bottom: 20px; }} .element-list {{ list-style: none; padding: 0; }} .element-item {{ padding: 15px; margin: 10px 0; background: #fafafa; border-left: 4px solid #4caf50; border-radius: 4px; }} .element-name {{ font-weight: bold; color: #333; font-size: 1.1em; }} .element-text {{ color: #666; margin-top: 5px; margin-left: 10px; }} .element-other-texts {{ color: #999; font-size: 0.9em; margin-top: 5px; margin-left: 10px; }} </style> </head> <body> <div class="container"> <h1>  - ?/h1> <div class="info"> <p><strong>?/strong>UIActivityMain?/p> <p><strong>?/strong> > </p> <p><strong></strong>{len(results)} ?/p> <p><strong>?/strong></p> </div> <ul class="element-list"> """ 
 for i, result in enumerate(results, 1): html_content += f""" <li class="element-item"> <div class="element-name">{i}. {result['name']}</div> <div class="element-text"> : {result['primary_text']}</div> """ 
 if len(result['sibling_texts']) > 1: other_texts = ', '.join(result['sibling_texts'][1:]) html_content += f' <div class="element-other-texts"> : {other_texts}</div>\n' html_content += " </li>\n" html_content += """ </ul> </div> </body> </html>""" html_file = as_abs_path('reports/runtime_capture/clickcontent_with_sibling_texts_{timestamp}.html')
 with open(html_file, 'w', encoding='utf-8') as f: f.write(html_content)
 print(f"?HTML? {html_file}")
 return html_file if __name__ == '__main__': main() 


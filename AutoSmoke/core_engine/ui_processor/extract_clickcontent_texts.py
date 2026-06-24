"""from AutoSmoke.path_utils import as_abs_pathClickContent?ext """ import json def extract_text_from_node(node): """ ? """ texts = []
 if not isinstance(node, dict):
 return texts payload = node.get('payload', {}) text = payload.get('text', '').strip() # ?
 if text and any('\u4e00' <= c <= '\u9fff' for c in text): texts.append(text) # ? children = node.get('children', [])
 if isinstance(children, list):
 for child in children: texts.extend(extract_text_from_node(child))
 return texts def find_clickcontent_with_texts(ui_tree): """ lickContent? """ results = []
 def traverse(node, depth=0):
 if not isinstance(node, dict):
 return payload = node.get('payload', {}) name = payload.get('name', '') # lickContent 
 if 'ClickContent' in name: visible = payload.get('visible', True)
 if visible: # ? texts = extract_text_from_node(node) #  # ? results.append({ 'name': name, 'texts': texts, 'primary_text': texts[0] if texts else '(?' }) # ? children = node.get('children', [])
 if isinstance(children, list):
 for child in children: traverse(child, depth + 1) traverse(ui_tree)
 return results def main(): # UI?
 with open(as_abs_path('reports/runtime_capture/ui_tree_20260611_121626.json'), 'r', encoding='utf-8') as f: ui_tree = json.load(f)
 print("=" * 60)
 print("ClickContent?)
 print("=" * 60) # lickContent results = find_clickcontent_with_texts(ui_tree)
 print(f"\n {len(results)} ClickContentn")
 for i, result in enumerate(results, 1):
 print(f"{i}. {result['name']}")
 print(f" : {result['primary_text']}")
 if len(result['texts']) > 1:
 print(f" : {', '.join(result['texts'][1:])}")
 print() # ? timestamp = '20260611_121626' output_file = as_abs_path('reports/runtime_capture/clickcontent_with_texts_{timestamp}.json')
 with open(output_file, 'w', encoding='utf-8') as f: json.dump(results, f, ensure_ascii=False, indent=2)
 print(f"?? {output_file}") # HTML html_content = f"""<!DOCTYPE html> <html> <head> <meta charset="utf-8"> <title> - ?/title> <style> body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }} .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }} h1 {{ color: #333; }} .info {{ background: #e8f5e9; padding: 10px; border-radius: 4px; margin-bottom: 20px; }} .element-list {{ list-style: none; padding: 0; }} .element-item {{ padding: 15px; margin: 10px 0; background: #fafafa; border-left: 4px solid #4caf50; border-radius: 4px; }} .element-name {{ font-weight: bold; color: #333; font-size: 1.1em; }} .element-text {{ color: #666; margin-top: 5px; margin-left: 10px; }} .element-other-texts {{ color: #999; font-size: 0.9em; margin-top: 5px; margin-left: 10px; }} </style> </head> <body> <div class="container"> <h1>  - ?/h1> <div class="info"> <p><strong>?/strong>UIActivityMain?/p> <p><strong>?/strong> > </p> <p><strong></strong>{len(results)} ?/p> <p><strong>?/strong>?/p> </div> <ul class="element-list"> """ 
 for i, result in enumerate(results, 1): html_content += f""" <li class="element-item"> <div class="element-name">{i}. {result['name']}</div> <div class="element-text"> : {result['primary_text']}</div> """ 
 if len(result['texts']) > 1: other_texts = ', '.join(result['texts'][1:]) html_content += f' <div class="element-other-texts"> : {other_texts}</div>\n' html_content += " </li>\n" html_content += """ </ul> </div> </body> </html>""" html_file = as_abs_path('reports/runtime_capture/clickcontent_with_texts_{timestamp}.html')
 with open(html_file, 'w', encoding='utf-8') as f: f.write(html_content)
 print(f"?HTML? {html_file}")
 return html_file if __name__ == '__main__': main() 


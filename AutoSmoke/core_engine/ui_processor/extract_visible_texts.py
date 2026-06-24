"""from AutoSmoke.path_utils import as_abs_path  """ import json def extract_visible_texts(node, visible_texts=None, depth=0): """ ? ?visible=True ?active=True ? """ 
 if visible_texts is None: visible_texts = []
 if not isinstance(node, dict):
 return visible_texts payload = node.get('payload', {}) # ? visible = payload.get('visible', True) #  active = node.get('active', True) # ? #  
 if not visible or not active:
 return visible_texts #  text = payload.get('text', '').strip()
 if text and any('\u4e00' <= c <= '\u9fff' for c in text): visible_texts.append(text) # ? children = node.get('children', [])
 if isinstance(children, list):
 for child in children: extract_visible_texts(child, visible_texts, depth + 1)
 return visible_texts def main(): # UI?
 with open(as_abs_path('reports/runtime_capture/ui_tree_20260611_120143.json'), 'r', encoding='utf-8') as f: ui_tree = json.load(f)
 print("=" * 60)
 print("?)
 print("=" * 60) #  visible_texts = extract_visible_texts(ui_tree) # ? unique_texts = list(set(visible_texts)) unique_texts.sort()
 print(f"\n {len(unique_texts)} n")
 for i, text in enumerate(unique_texts, 1):
 print(f"{i}. {text}") # ? output_file = as_abs_path('reports/runtime_capture/visible_chinese_texts.txt')
 with open(output_file, 'w', encoding='utf-8') as f: f.write("n") f.write("=" * 60 + "\n\n")
 for i, text in enumerate(unique_texts, 1): f.write(f"{i}. {text}\n")
 print(f"\n?: {output_file}") # HTML html_content = """<!DOCTYPE html> <html> <head> <meta charset="utf-8"> <title></title> <style> body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; } .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); } h1 { color: #333; } .info { background: #e8f5e9; padding: 10px; border-radius: 4px; margin-bottom: 20px; } .text-list { list-style: none; padding: 0; } .text-item { padding: 10px 15px; margin: 5px 0; background: #fafafa; border-left: 4px solid #4caf50; border-radius: 4px; } .text-index { color: #666; font-size: 0.9em; margin-right: 10px; } </style> </head> <body> <div class="container"> <h1>??/h1> <div class="info"> <p><strong>?/strong>UIActivityMain?/p> <p><strong></strong></p> <p><strong>?/strong>""" + str(len(unique_texts)) + """ ?/p> <p><strong>?/strong>?/p> </div> <ul class="text-list"> """ 
 for i, text in enumerate(unique_texts, 1): html_content += f' <li class="text-item"><span class="text-index">{i}.</span> {text}</li>\n' html_content += """ </ul> </div> </body> </html>""" html_file = as_abs_path('reports/runtime_capture/visible_chinese_texts.html')
 with open(html_file, 'w', encoding='utf-8') as f: f.write(html_content)
 print(f"?HTML? {html_file}")
 return html_file if __name__ == '__main__': main() 

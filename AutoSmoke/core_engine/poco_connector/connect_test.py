"""from AutoSmoke.path_utils import as_abs_pathIUI """ from poco.drivers.std import StdPoco import json
class MockDevice:
    def __init__(self): self.uuid = 'localhost:5001'
    def display_info(self):
        return {'width': 1170, 'height': 2532}
        def get_default_device(self, **kw):
            return self
            def touch(self, *a, **kw):
                pass
                def swipe(self, *a, **kw):
                    pass
                    def snapshot(self, *a, **kw):
                        pass
                        dev = MockDevice() poco = StdPoco(5001, dev, ip='localhost') print(f"?? {poco.get_screen_size()}\n")
                        raw = poco.agent.hierarchy.dump()
                        def find_canvases(node, path=""): """anvasanvasI?"" payload = node.get('payload', {}) name = node.get('name', '') children = node.get('children', []) components = str(payload.get('components', [])) # anvasCanvas is_canvas = "'Canvas'" in components or "'CanvasScaler'" in components
                        result = []
                        if is_canvas: # Canvas?XXX(Clone) [ ? display_name = name full_texts = extract_all_texts(node)
                        result.append({ 'name': display_name, 'full_texts': full_texts, 'node': node, 'path': path })
                        for child in children:
                            result.extend(find_canvases(child, f"{path}/{name}"))
                            return result def extract_all_texts(node, depth=0, max_d=8): """""" texts = [] payload = node.get('payload', {}) children = node.get('children', []) text = payload.get('text', '')
                            if text and depth < max_d: texts.append(text)
                            for child in children: texts.extend(extract_all_texts(child, depth+1, max_d))
                            return texts def list_all_uis(node, depth=0, max_depth=10): """I Canvas""" canvases = find_canvases(node) lines = [] lines.append(f"?{len(canvases)} I\n")
                            for i, canvas in enumerate(canvases): lines.append(f"{'='*60}") lines.append(f"{i+1}: {canvas['name']}") lines.append(f"{'='*60}") # anvas? elems = extract_elements(canvas['node'])
                            if elems: lines.append(" [")
                            for elem in elems: lines.append(f" {elem}") # ?
                            if canvas['full_texts']: unique_texts = list(dict.fromkeys(canvas['full_texts'])) #  lines.append(" []")
                            for t in unique_texts: lines.append(f"  {t}") lines.append("")
                            return '\n'.join(lines)
                            def extract_elements(node, depth=0, max_d=6): """?"" elements = [] payload = node.get('payload', {}) name = node.get('name', '') children = node.get('children', [])
                            if depth > max_d:
                                return elements components = str(payload.get('components', [])) text = payload.get('text', '') texture = payload.get('texture', '') has_event = 'EventTriggerListener' in components is_button = "'Button'" in components has_tfwtext = "'TFWText'" in components or "'Text'" in components is_clickable = has_event or is_button
                                if is_clickable or (has_tfwtext and text): label = f" {' ' * depth}[{name}]"
                                if text: label += f" ='{text}'"
                                if texture and not texture.startswith('RGBA'): label += f" ='{texture}'"
                                if is_clickable: label += " " elements.append(label)
                                for child in children: elements.extend(extract_elements(child, depth+1, max_d))
                                return elements output = list_all_uis(raw) #  with open(as_abs_path('ui_windows.txt'), 'w', encoding='utf-8') as f: f.write(output)
                                print(output[:3000]) # ?000 print(f"...\n\n?UI: {AUTOSMOKE_REPORT_DIR}/ui_windows.txt")


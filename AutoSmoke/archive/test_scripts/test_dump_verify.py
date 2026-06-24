from airtest.core.api import *
from poco.drivers.unity3d import UnityPoco
import time, json, os
from pathlib import Path

auto_setup(os.path.abspath(__file__))
init_device('Windows')
time.sleep(1)

poco = UnityPoco()
print('[rpc]connected')

ui_tree = poco.dump()
print('dump success, data length:', len(str(ui_tree)))

# 保存到文件
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_file = str(Path(__file__).parent.parent / 'reports' / 'runtime_capture' / 'ui_tree_') + timestamp + ".json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(ui_tree, f, ensure_ascii=False, indent=2)
print("UI tree saved:", output_file)

# 检查 ClickContent 是否有 text
def find_clickcontent(obj, results=None, path=''):
    if results is None:
        results = []
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        if 'ClickContent' in name:
            text = payload.get('text', '')
            visible = payload.get('visible', True)
            results.append({'path': path, 'text': text, 'visible': visible})
        for key, val in obj.items():
            find_clickcontent(val, results, path + '.' + str(key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_clickcontent(item, results, path + '[' + str(i) + ']')
    return results

results = find_clickcontent(ui_tree)
print("\n找到", len(results), "个 ClickContent 节点：")
for i, r in enumerate(results[:15], 1):
    text_str = r['text'][:40] if r['text'] else '(空)'
    print("  " + str(i) + ". text=" + text_str + "  visible=" + str(r["visible"]))
if len(results) > 15:
    print("  ... 共 " + str(len(results)) + " 个")

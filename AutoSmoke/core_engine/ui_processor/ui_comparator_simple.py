#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
绠€鍖栫殑UI瀵规瘮宸ュ叿
瀵规瘮闈欐€佷唬鐮佸垎鏋愬拰杩愯鏃禪I鏍戯紝鎵惧嚭宸紓
涓嶉渶瑕佽繛鎺oco锛岀洿鎺ヨ鍙朖SON鏂囦欢
"""

import sys
import os
import json
from datetime import datetime
from collections import defaultdict

class SimpleUIComparator:
    """绠€鍖栫殑UI瀵规瘮鍣?- 涓嶉渶瑕丳oco杩炴帴"""
    
    def __init__(self, static_json, runtime_json):
        """
        鍒濆鍖栧姣斿櫒
        :param static_json: 闈欐€佸垎鏋怞SON鏂囦欢
        :param runtime_json: 杩愯鏃禪I鏍慗SON鏂囦欢
        """
        self.static_data = self._load_json(static_json, "闈欐€佸垎鏋?)
        self.runtime_data = self._load_json(runtime_json, "杩愯鏃禪I鏍?)
        
        self.comparison_results = {
            'only_in_static': [],      # 鍙湪闈欐€佸垎鏋愪腑瀛樺湪
            'only_in_runtime': [],     # 鍙湪杩愯鏃跺瓨鍦?            'in_both': [],             # 涓よ€呴兘瀛樺湪
            'summary': {}
        }
    
    def _load_json(self, file_path, description):
        """鍔犺浇JSON鏂囦欢"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"鉁?宸插姞杞絳description}: {file_path}")
            return data
        except Exception as e:
            print(f"鉂?鍔犺浇{description}澶辫触: {e}")
            return None
    
    def extract_runtime_clickable(self):
        """浠庤繍琛屾椂UI鏍戜腑鎻愬彇鍙偣鍑诲厓绱?""
        if not self.runtime_data:
            return []
        
        clickable_elements = []
        
        def traverse(node, parent_path=""):
            """閫掑綊閬嶅巻UI鏍?""
            if not node:
                return
            
            node_name = node.get('name', 'Unknown')
            node_type = node.get('type', '')
            node_path = f"{parent_path}/{node_name}" if parent_path else node_name
            
            # 鍒ゆ柇鏄惁涓哄彲鐐瑰嚮鍏冪礌
            is_clickable = self._is_clickable(node)
            
            if is_clickable:
                clickable_elements.append({
                    'name': node_name,
                    'type': node_type,
                    'path': node_path,
                    'clickable': is_clickable,
                    'pos': node.get('pos', [0, 0]),
                    'size': node.get('size', [0, 0])
                })
            
            # 閫掑綊澶勭悊瀛愯妭鐐?            children = node.get('children', [])
            for child in children:
                traverse(child, node_path)
        
        # 寮€濮嬮亶鍘?        traverse(self.runtime_data)
        
        print(f"浠庤繍琛屾椂UI鏍戜腑鎻愬彇浜?{len(clickable_elements)} 涓彲鐐瑰嚮鍏冪礌")
        return clickable_elements
    
    def _is_clickable(self, node):
        """鍒ゆ柇鑺傜偣鏄惁鍙偣鍑?""
        # 鏂规硶1: 妫€鏌lickable灞炴€?        if node.get('clickable', False):
            return True
        
        # 鏂规硶2: 妫€鏌ヨ妭鐐圭被鍨?        node_type = node.get('type', '')
        if 'Button' in node_type:
            return True
        
        # 鏂规硶3: 妫€鏌ヨ妭鐐瑰悕绉板叧閿瘝
        node_name = node.get('name', '')
        clickable_keywords = ['Button', 'Btn', 'Click', 'btn', 'button', '纭', '鍙栨秷', '鍏抽棴']
        if any(keyword in node_name for keyword in clickable_keywords):
            return True
        
        return False
    
    def compare(self):
        """瀵规瘮闈欐€佸垎鏋愪笌杩愯鏃剁粨鏋?""
        print("\n" + "=" * 60)
        print("馃攳 寮€濮嬪姣斿垎鏋?..")
        print("=" * 60)
        
        if not self.static_data or not self.runtime_data:
            print("鉂?鏁版嵁涓嶅畬鏁达紝鏃犳硶瀵规瘮")
            return None
        
        # 鎻愬彇闈欐€佸垎鏋愪腑鐨勬墍鏈塙I鍏冪礌鍚嶇О
        static_element_names = set()
        static_element_map = defaultdict(list)
        
        for ui_class in self.static_data:
            for elem in ui_class.get('clickable_elements', []):
                elem_name = elem.get('likely_name_in_ui', '').lower()
                if elem_name:
                    static_element_names.add(elem_name)
                    static_element_map[elem_name].append({
                        'class': ui_class['class'],
                        'file': ui_class['file'],
                        'field': elem['field_name'],
                        'handler': elem.get('handler', '')
                    })
        
        # 鎻愬彇杩愯鏃朵腑鐨勬墍鏈塙I鍏冪礌鍚嶇О
        runtime_elements = self.extract_runtime_clickable()
        runtime_element_names = set()
        runtime_element_map = {}
        
        for elem in runtime_elements:
            elem_name = elem['name'].lower()
            runtime_element_names.add(elem_name)
            runtime_element_map[elem_name] = elem
        
        # 瀵规瘮
        only_in_static = static_element_names - runtime_element_names
        only_in_runtime = runtime_element_names - static_element_names
        in_both = static_element_names & runtime_element_names
        
        # 淇濆瓨缁撴灉
        self.comparison_results['only_in_static'] = [
            {'name': name, 'details': static_element_map[name]}
            for name in only_in_static
        ]
        
        self.comparison_results['only_in_runtime'] = [
            {'name': name, 'details': runtime_element_map[name]}
            for name in only_in_runtime
        ]
        
        self.comparison_results['in_both'] = [
            {
                'name': name, 
                'static': static_element_map.get(name, []), 
                'runtime': runtime_element_map.get(name, {})
            }
            for name in in_both
        ]
        
        # 缁熻
        self.comparison_results['summary'] = {
            'static_count': len(static_element_names),
            'runtime_count': len(runtime_element_names),
            'only_in_static_count': len(only_in_static),
            'only_in_runtime_count': len(only_in_runtime),
            'in_both_count': len(in_both)
        }
        
        # 鎵撳嵃鎽樿
        self._print_comparison_summary()
        
        return self.comparison_results
    
    def _print_comparison_summary(self):
        """鎵撳嵃瀵规瘮鎽樿"""
        summary = self.comparison_results['summary']
        
        print("\n" + "=" * 60)
        print("馃搳 瀵规瘮缁撴灉鎽樿")
        print("=" * 60)
        print(f"闈欐€佸垎鏋愬彂鐜? {summary['static_count']} 涓彲鐐瑰嚮鍏冪礌")
        print(f"杩愯鏃舵崟鑾? {summary['runtime_count']} 涓彲鐐瑰嚮鍏冪礌")
        print(f"\n鉁?涓よ€呴兘瀛樺湪: {summary['in_both_count']} 涓?)
        print(f"鈿狅笍  鍙湪闈欐€佸垎鏋愪腑瀛樺湪: {summary['only_in_static_count']} 涓?(鍙兘鏄殣钘廢I)")
        print(f"鉂?鍙湪杩愯鏃朵腑瀛樺湪: {summary['only_in_runtime_count']} 涓?(鍙兘鏄姩鎬佺敓鎴?")
        
        # 鎵撳嵃绀轰緥
        if self.comparison_results['only_in_static']:
            print(f"\n鈿狅笍  鍙湪闈欐€佸垎鏋愪腑鐨刄I鍏冪礌 (鍓?0涓?:")
            for i, elem in enumerate(self.comparison_results['only_in_static'][:10]):
                print(f"   {i+1}. {elem['name']} (鍦ㄧ被 {elem['details'][0]['class']} 涓?")
        
        if self.comparison_results['only_in_runtime']:
            print(f"\n鉂?鍙湪杩愯鏃朵腑鐨刄I鍏冪礌 (鍓?0涓?:")
            for i, elem in enumerate(self.comparison_results['only_in_runtime'][:10]):
                print(f"   {i+1}. {elem['name']} (绫诲瀷: {elem['details'].get('type', 'Unknown')})")
    
    def save_results(self, output_dir=as_abs_path("reports/comparison")):
        """淇濆瓨瀵规瘮缁撴灉"""
        if not self.comparison_results.get('summary'):
            print("鈿狅笍  娌℃湁瀵规瘮缁撴灉锛岃鍏堣繍琛?compare()")
            return None, None
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 淇濆瓨JSON
        json_path = os.path.join(output_dir, f"ui_comparison_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.comparison_results, f, ensure_ascii=False, indent=2)
        
        # 鐢熸垚HTML鎶ュ憡
        html_path = os.path.join(output_dir, f"ui_comparison_report_{timestamp}.html")
        self._generate_html_report(html_path, timestamp)
        
        print(f"\n鉁?瀵规瘮缁撴灉宸蹭繚瀛?")
        print(f"   JSON: {json_path}")
        print(f"   HTML: {html_path}")
        
        return json_path, html_path
    
    def _generate_html_report(self, output_path, timestamp):
        """鐢熸垚HTML瀵规瘮鎶ュ憡"""
        summary = self.comparison_results['summary']
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>UI瀵规瘮鎶ュ憡 - {timestamp}</title>
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .section {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .element {{ 
                    background: #ecf0f1; 
                    padding: 10px; 
                    margin: 10px 0; 
                    border-left: 4px solid #3498db;
                    border-radius: 3px;
                }}
                .element-static {{ border-left-color: #e74c3c; }}
                .element-runtime {{ border-left-color: #f39c12; }}
                .element-both {{ border-left-color: #27ae60; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; flex-wrap: wrap; }}
                .stat-box {{ text-align: center; padding: 20px; background: #ecf0f1; border-radius: 5px; min-width: 120px; margin: 10px; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
                .stat-label {{ color: #7f8c8d; }}
                .hidden-ui {{ background: #fff3cd; border-left-color: #ffc107; }}
                .dynamic-ui {{ background: #d1ecf1; border-left-color: #17a2b8; }}
                pre {{ background: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 3px; overflow-x: auto; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>馃攳 UI鍏冪礌瀵规瘮鎶ュ憡</h1>
                <p>鐢熸垚鏃堕棿: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>瀵规瘮: 闈欐€佷唬鐮佸垎鏋?vs Poco杩愯鏃舵崟鑾?/p>
            </div>
            
            <div class="summary">
                <h2>馃搳 缁熻鎽樿</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-number">{summary['static_count']}</div>
                        <div class="stat-label">闈欐€佸垎鏋?/div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{summary['runtime_count']}</div>
                        <div class="stat-label">杩愯鏃舵崟鑾?/div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{summary['in_both_count']}</div>
                        <div class="stat-label">涓よ€呴兘瀛樺湪</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{summary['only_in_static_count']}</div>
                        <div class="stat-label">浠呴潤鎬佸垎鏋?/div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{summary['only_in_runtime_count']}</div>
                        <div class="stat-label">浠呰繍琛屾椂</div>
                    </div>
                </div>
            </div>
        """
        
        # 鍙湪闈欐€佸垎鏋愪腑鐨刄I鍏冪礌 (鍙兘鏄殣钘廢I)
        if self.comparison_results['only_in_static']:
            html_content += """
            <div class="section">
                <h2>鈿狅笍 鍙湪闈欐€佸垎鏋愪腑瀛樺湪 ({}) - 鍙兘鏄殣钘廢I</h2>
                <p>杩欎簺UI鍏冪礌鍦ㄤ唬鐮佷腑瀛樺湪锛屼絾褰撳墠杩愯鏃舵湭鎹曡幏鍒帮紝鍙兘鏄?</p>
                <ul>
                    <li>琚玈etActive(false)闅愯棌</li>
                    <li>闇€瑕佺壒瀹氭潯浠舵墠鏄剧ず</li>
                    <li>鍦ㄥ叾瀹冪晫闈腑</li>
                </ul>
            """.format(len(self.comparison_results['only_in_static']))
            
            for elem in self.comparison_results['only_in_static'][:50]:  # 鍙樉绀哄墠50涓?                html_content += f"""
                <div class="element element-static hidden-ui">
                    <h4>{elem['name']}</h4>
                    <pre>"""
                for detail in elem['details']:
                    html_content += f"绫? {detail['class']}\n鏂囦欢: {detail['file']}\n瀛楁: {detail['field']}"
                    if detail.get('handler'):
                        html_content += f"\n浜嬩欢澶勭悊: {detail['handler']}"
                    html_content += "\n\n"
                html_content += """</pre>
                </div>
                """
            
            html_content += """
            </div>
            """
        
        # 鍙湪杩愯鏃朵腑鐨刄I鍏冪礌 (鍙兘鏄姩鎬佺敓鎴?
        if self.comparison_results['only_in_runtime']:
            html_content += """
            <div class="section">
                <h2>鉂?鍙湪杩愯鏃朵腑瀛樺湪 ({}) - 鍙兘鏄姩鎬佺敓鎴怳I</h2>
                <p>杩欎簺UI鍏冪礌鍦ㄨ繍琛屾椂瀛樺湪锛屼絾闈欐€佸垎鏋愪腑鏈壘鍒帮紝鍙兘鏄?</p>
                <ul>
                    <li>鍔ㄦ€佺敓鎴愮殑UI</li>
                    <li>绗笁鏂筓I搴?/li>
                    <li>闈欐€佸垎鏋愭湭瑕嗙洊鐨勪唬鐮?/li>
                </ul>
            """.format(len(self.comparison_results['only_in_runtime']))
            
            for elem in self.comparison_results['only_in_runtime'][:50]:  # 鍙樉绀哄墠50涓?                details = elem['details']
                html_content += f"""
                <div class="element element-runtime dynamic-ui">
                    <h4>{elem['name']}</h4>
                    <p>绫诲瀷: {details.get('type', 'Unknown')}</p>
                    <p>璺緞: <code>{details.get('path', 'Unknown')}</code></p>
                    <p>浣嶇疆: x={details.get('pos', [0,0])[0]:.3f}, y={details.get('pos', [0,0])[1]:.3f}</p>
                </div>
                """
            
            html_content += """
            </div>
            """
        
        # 涓よ€呴兘瀛樺湪鐨刄I鍏冪礌
        if self.comparison_results['in_both']:
            html_content += """
            <div class="section">
                <h2>鉁?涓よ€呴兘瀛樺湪 ({})</h2>
                <p>杩欎簺UI鍏冪礌鍦ㄩ潤鎬佸垎鏋愬拰杩愯鏃堕兘瀛樺湪锛屽睘浜庢甯窾I鍏冪礌銆?/p>
            """.format(len(self.comparison_results['in_both']))
            
            for elem in self.comparison_results['in_both'][:50]:  # 鍙樉绀哄墠50涓?                html_content += f"""
                <div class="element element-both">
                    <h4>{elem['name']}</h4>
                    <p>闈欐€佸垎鏋? 鍦?{len(elem['static'])} 涓被涓壘鍒?/p>
                    <p>杩愯鏃? 宸叉崟鑾?(璺緞: {elem['runtime'].get('path', 'Unknown')})</p>
                </div>
                """
            
            html_content += """
            </div>
            """
        
        html_content += """
            <hr>
            <p><em>鎶ュ憡鐢熸垚宸ュ叿: Simple UI Comparator v1.0</em></p>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


def main():
    """涓诲嚱鏁?""
    print("=" * 60)
    print("馃攳 绠€鍖朥I瀵规瘮宸ュ叿")
    print("   瀵规瘮闈欐€佷唬鐮佸垎鏋?vs Poco杩愯鏃舵崟鑾?)
    print("=" * 60)
    
    # 鏂囦欢璺緞
    static_json = as_abs_path("reports\static_ui\static_ui_analysis_20260611_095903.json")
    runtime_json = as_abs_path("reports\runtime_capture\runtime_ui_20260611_101112.json")
    
    # 妫€鏌ユ枃浠舵槸鍚﹀瓨鍦?    if not os.path.exists(static_json):
        print(f"鉂?閿欒: 闈欐€佸垎鏋愭枃浠朵笉瀛樺湪 {static_json}")
        print("璇峰厛杩愯 static_ui_analyzer.py 鐢熸垚闈欐€佸垎鏋愭姤鍛?)
        return
    
    if not os.path.exists(runtime_json):
        print(f"鉂?閿欒: 杩愯鏃禪I鏂囦欢涓嶅瓨鍦?{runtime_json}")
        print("璇峰厛杩愯 test_poco_connection_fixed.py 鑾峰彇杩愯鏃禪I鏍?)
        return
    
    # 鍒涘缓瀵规瘮鍣?    comparator = SimpleUIComparator(static_json, runtime_json)
    
    # 瀵规瘮
    results = comparator.compare()
    
    if not results:
        print("\n鉂?瀵规瘮澶辫触")
        return
    
    # 淇濆瓨缁撴灉
    json_path, html_path = comparator.save_results()
    
    print(f"\n鉁?瀵规瘮瀹屾垚!")
    print(f"   鎶ュ憡: {html_path}")
    
    # 鑷姩鎵撳紑鎶ュ憡
    try:
        os.startfile(html_path)
    except:
        pass


if __name__ == "__main__":
    main()


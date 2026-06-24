#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
涓诲煄鐣岄潰UI绫绘煡鎵惧櫒
浠庨潤鎬佸垎鏋愮粨鏋滀腑鏌ユ壘涓诲煄鐣岄潰鐩稿叧鐨刄I绫?"""

import json
import re
from difflib import get_close_matches

def find_main_city_ui_classes(json_file):
    """鏌ユ壘涓诲煄鐣岄潰鐩稿叧鐨刄I绫?""
    print("=" * 80)
    print("涓诲煄鐣岄潰UI绫绘煡鎵惧櫒")
    print("=" * 80)
    
    # 璇诲彇闈欐€佸垎鏋愮粨鏋?    print(f"\n璇诲彇闈欐€佸垎鏋愮粨鏋? {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"鍏卞姞杞?{len(results)} 涓猆I绫?)
    
    # 涓诲煄鐩稿叧鍏抽敭璇?    main_city_keywords = [
        'maincity', 'main_city', 'maincityui', 'uimaincity',
        'city', 'uicity', 'cityui',
        'town', 'uitown', 'townui',
        'home', 'uihome', 'homeui',
        'main', 'uimain', 'mainui',
        'hud', 'uihud', 'hudui', 'hudmain', 'mainhud'
    ]
    
    # 鏌ユ壘鍖归厤鐨刄I绫?    print("\n鏌ユ壘涓诲煄鐣岄潰鐩稿叧鐨刄I绫?..")
    matched_classes = []
    
    for result in results:
        class_name = result['ui_class'].lower()
        
        # 妫€鏌ユ槸鍚﹀寘鍚叧閿瘝
        for keyword in main_city_keywords:
            if keyword in class_name:
                matched_classes.append(result)
                break
    
    print(f"鎵惧埌 {len(matched_classes)} 涓彲鑳界殑涓诲煄UI绫?)
    
    # 鎸夊彲鐐瑰嚮鍏冪礌鏁伴噺鎺掑簭
    matched_classes.sort(key=lambda x: len(x['clickable_elements']), reverse=True)
    
    # 鏄剧ず鍓?0涓渶鐩稿叧鐨刄I绫?    print("\n鏈€鐩稿叧鐨刄I绫?")
    for i, result in enumerate(matched_classes[:10]):
        print(f"  {i+1}. {result['ui_class']} - {len(result['clickable_elements'])} 涓彲鐐瑰嚮鍏冪礌")
        print(f"     鏂囦欢: {result['file']}")
    
    return matched_classes

def display_ui_class_details(ui_class):
    """鏄剧ずUI绫荤殑璇︾粏淇℃伅"""
    print("\n" + "=" * 80)
    print(f"UI绫? {ui_class['ui_class']}")
    print("=" * 80)
    print(f"鏂囦欢: {ui_class['file']}")
    print(f"鍩虹被: {ui_class['base_class']}")
    print(f"鍙偣鍑诲厓绱犳暟閲? {len(ui_class['clickable_elements'])}")
    
    # 鏄剧ず鍙偣鍑诲厓绱?    print("\n鍙偣鍑诲厓绱?")
    for i, elem in enumerate(ui_class['clickable_elements']):
        print(f"  {i+1}. {elem['field_name']} ({elem['type']})")
        print(f"      UI涓彲鑳藉悕绉? {elem['likely_name_in_ui']}")
        if 'handler' in elem:
            print(f"      浜嬩欢澶勭悊: {elem['handler']}")
    
    # 鏄剧ず浜嬩欢缁戝畾
    if ui_class['event_bindings']:
        print("\n浜嬩欢缁戝畾:")
        for i, binding in enumerate(ui_class['event_bindings']):
            print(f"  {i+1}. {binding['type']}: {binding['target']} -> {binding['handler']}")

def generate_main_city_report(matched_classes, output_file):
    """鐢熸垚涓诲煄鐣岄潰鎶ュ憡"""
    print(f"\n鐢熸垚涓诲煄鐣岄潰鎶ュ憡: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("涓诲煄鐣岄潰鍙偣鍑诲厓绱犳姤鍛奬n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"鎵惧埌 {len(matched_classes)} 涓彲鑳界殑涓诲煄UI绫籠n\n")
        
        for i, ui_class in enumerate(matched_classes):
            f.write("-" * 80 + "\n")
            f.write(f"[{i+1}] UI绫? {ui_class['ui_class']}\n")
            f.write(f"    鏂囦欢: {ui_class['file']}\n")
            f.write(f"    鍩虹被: {ui_class['base_class']}\n")
            f.write(f"    鍙偣鍑诲厓绱犳暟閲? {len(ui_class['clickable_elements'])}\n\n")
            
            f.write("    鍙偣鍑诲厓绱?\n")
            for j, elem in enumerate(ui_class['clickable_elements']):
                f.write(f"      {j+1}. {elem['field_name']} ({elem['type']})\n")
                f.write(f"         UI涓彲鑳藉悕绉? {elem['likely_name_in_ui']}\n")
                if 'handler' in elem:
                    f.write(f"         浜嬩欢澶勭悊: {elem['handler']}\n")
            
            f.write("\n")
    
    print(f"鉁?鎶ュ憡宸茬敓鎴? {output_file}")

def main():
    """涓诲嚱鏁?""
    # 闈欐€佸垎鏋愮粨鏋滄枃浠?    json_file = as_abs_path("reports\static_ui\static_ui_analysis_20260611_111322.json")
    
    # 鏌ユ壘涓诲煄鐣岄潰鐩稿叧鐨刄I绫?    matched_classes = find_main_city_ui_classes(json_file)
    
    if not matched_classes:
        print("\n鉂?鏈壘鍒颁富鍩庣晫闈㈢浉鍏崇殑UI绫?)
        print("寤鸿:")
        print("  1. 妫€鏌I绫诲悕鏄惁鍖呭惈'MainCity'銆?City'绛夊叧閿瘝")
        print("  2. 鎵嬪姩鎸囧畾UI绫诲悕")
        return
    
    # 璁╃敤鎴烽€夋嫨UI绫?    print("\n璇烽€夋嫨瑕佹煡鐪嬬殑UI绫?(杈撳叆搴忓彿锛屾垨杈撳叆'all'鏌ョ湅鎵€鏈?:")
    choice = input("> ")
    
    if choice.lower() == 'all':
        # 鏄剧ず鎵€鏈夊尮閰嶇殑UI绫?        for ui_class in matched_classes:
            display_ui_class_details(ui_class)
    else:
        # 鏄剧ず閫夊畾鐨刄I绫?        try:
            index = int(choice) - 1
            if 0 <= index < len(matched_classes):
                display_ui_class_details(matched_classes[index])
            else:
                print(f"鉂?鏃犳晥鐨勫簭鍙? {choice}")
        except ValueError:
            print(f"鉂?鏃犳晥鐨勮緭鍏? {choice}")
    
    # 鐢熸垚鎶ュ憡
    output_file = as_abs_path("reports\main_city\main_city_report.txt")
    generate_main_city_report(matched_classes, output_file)

if __name__ == "__main__":
    main()


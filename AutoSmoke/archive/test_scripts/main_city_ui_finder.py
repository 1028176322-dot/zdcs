#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主城界面可点击元素查找器
从静态分析结果中查找主城界面相关的UI类，并显示可点击元素
"""

import json
import os
from datetime import datetime
from pathlib import Path

def find_main_city_ui_classes(json_file):
    """查找主城界面相关的UI类"""
    print("=" * 80)
    print("主城界面可点击元素查找器")
    print("=" * 80)
    
    # 读取静态分析结果
    print(f"\n读取静态分析结果: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"共加载 {len(results)} 个UI类")
    
    # 主城相关关键词 - 扩展版
    main_city_keywords = [
        'maincity', 'main_city', 'maincityui', 'uimaincity',
        'city', 'uicity', 'cityui', 'uicitymain',
        'town', 'uitown', 'townui',
        'home', 'uihome', 'homeui', 'ui_main', 'main_ui',
        'hud', 'uihud', 'hudui', 'hudmain', 'mainhud', 'hud_main',
        'world', 'uiworld', 'worldui',
        'map', 'uimap', 'mapui',
        'build', 'uibuild', 'buildui',
        'castle', 'uicastle', 'castleui'
    ]
    
    # 查找匹配的UI类
    print("\n查找主城界面相关的UI类...")
    matched_classes = []
    
    for result in results:
        class_name = result['ui_class'].lower()
        file_path = result['file'].lower()
        
        # 检查类名或文件路径是否包含关键词
        matched = False
        for keyword in main_city_keywords:
            if keyword in class_name or keyword in file_path:
                matched = True
                break
        
        if matched:
            matched_classes.append(result)
    
    print(f"找到 {len(matched_classes)} 个可能的主城UI类")
    
    if not matched_classes:
        print("\n⚠️ 未找到明显的主城UI类")
        print("可能的原因:")
        print("  1. 主城UI类的命名不包含常见关键词")
        print("  2. 主城UI类没有使用EventTriggerListener或ButtonScale")
        print("  3. 主城UI类在分析结果中，但被归类到其他名称")
        print("\n建议:")
        print("  1. 请提供主城UI的类名或文件名")
        print("  2. 或者，我将显示所有UI类，您可以手动查找")
        return []
    
    # 按可点击元素数量排序
    matched_classes.sort(key=lambda x: len(x['clickable_elements']), reverse=True)
    
    # 显示前20个最相关的UI类
    print("\n最相关的UI类 (前20个):")
    for i, result in enumerate(matched_classes[:20]):
        print(f"  {i+1}. {result['ui_class']} - {len(result['clickable_elements'])} 个可点击元素")
        print(f"     文件: {result['file']}")
    
    return matched_classes

def display_ui_class_details(ui_class):
    """显示UI类的详细信息"""
    print("\n" + "=" * 80)
    print(f"UI类: {ui_class['ui_class']}")
    print("=" * 80)
    print(f"文件: {ui_class['file']}")
    print(f"基类: {ui_class['base_class']}")
    print(f"可点击元素数量: {len(ui_class['clickable_elements'])}")
    
    # 显示可点击元素
    if ui_class['clickable_elements']:
        print("\n可点击元素:")
        for i, elem in enumerate(ui_class['clickable_elements']):
            print(f"  {i+1}. {elem['field_name']} ({elem['type']})")
            print(f"      UI中可能名称: {elem['likely_name_in_ui']}")
            if 'handler' in elem and elem['handler'] != 'Unknown':
                print(f"      事件处理: {elem['handler']}")
    else:
        print("\n⚠️ 没有找到可点击元素")
    
    # 显示事件绑定
    if ui_class['event_bindings']:
        print("\n事件绑定:")
        for i, binding in enumerate(ui_class['event_bindings']):
            print(f"  {i+1}. {binding['type']}: {binding['target']} -> {binding['handler']}")

def generate_main_city_report(matched_classes, output_dir=str(Path(__file__).parent.parent / 'reports' / 'main_city')):
    """生成主城界面报告"""
    print(f"\n生成主城界面报告...")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存JSON
    json_path = os.path.join(output_dir, f"main_city_ui_classes_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(matched_classes, f, ensure_ascii=False, indent=2)
    
    # 生成HTML报告
    html_path = os.path.join(output_dir, f"main_city_report_{timestamp}.html")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>主城界面可点击元素报告 - {timestamp}</title>
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .summary {{ background: white; padding: 15px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .ui-class {{ 
                background: white; 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .ui-class:hover {{ box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
            .class-name {{ color: #2c3e50; font-size: 1.5em; font-weight: bold; }}
            .file-path {{ color: #7f8c8d; font-size: 0.9em; font-family: monospace; }}
            .element {{ 
                background: #ecf0f1; 
                padding: 10px; 
                margin: 10px 0; 
                border-left: 4px solid #3498db;
                border-radius: 3px;
            }}
            .element-name {{ font-weight: bold; color: #2980b9; }}
            .handler {{ color: #27ae60; font-family: monospace; }}
            .event-type {{ color: #e74c3c; font-size: 0.9em; }}
            pre {{ background: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏰 主城界面可点击元素报告</h1>
            <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>找到 {len(matched_classes)} 个可能的主城UI类</p>
        </div>
        
        <div class="summary">
            <h2>📊 统计摘要</h2>
            <p>主城UI类数量: <strong>{len(matched_classes)}</strong> 个</p>
            <p>可点击元素总数: <strong>{sum(len(r['clickable_elements']) for r in matched_classes)}</strong> 个</p>
        </div>
    """
    
    for i, result in enumerate(matched_classes):
        clickable_count = len(result['clickable_elements'])
        html_content += f"""
        <div class="ui-class">
            <div class="class-name">[{i+1}] {result['ui_class']}</div>
            <div class="file-path">📁 {result['file']}</div>
            <p><strong>基类:</strong> {result['base_class']}</p>
            
            <h3>🎯 可点击元素 ({clickable_count}个)</h3>
        """
        
        if clickable_count > 0:
            for elem in result['clickable_elements']:
                handler_str = f'<p>事件处理: <span class="handler">{elem.get("handler", "")}</span></p>' if 'handler' in elem and elem['handler'] != 'Unknown' else ''
                html_content += f"""
                <div class="element">
                    <div class="element-name">字段: {elem['field_name']}</div>
                    <p>类型: <span class="event-type">{elem['type']}</span></p>
                    <p>UI中可能名称: <code>{elem['likely_name_in_ui']}</code></p>
                    {handler_str}
                </div>
                """
        else:
            html_content += f"""
                <div class="element">
                    <p>⚠️ 没有找到可点击元素</p>
                </div>
                """
        
        if result['event_bindings']:
            html_content += f"""
            <h3>🔗 事件绑定</h3>
            <pre>"""
            for binding in result['event_bindings']:
                html_content += f"{binding['type']}: {binding['target']} -> {binding['handler']}\n"
            html_content += "</pre>"
        
        html_content += """
        </div>
        """
    
    html_content += """
        <hr>
        <p><em>报告生成工具: Main City UI Finder v1.0</em></p>
    </body>
    </html>
    """
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ 报告已生成:")
    print(f"  JSON: {json_path}")
    print(f"  HTML: {html_path}")
    
    return json_path, html_path

def main():
    """主函数"""
    # 静态分析结果文件
    json_file = r"E:\zdcs\AutoSmoke\reports\static_ui\static_ui_analysis_20260611_111322.json"
    
    if not os.path.exists(json_file):
        print(f"❌ 错误: 文件不存在 {json_file}")
        print("请先运行静态分析器")
        return
    
    # 查找主城界面相关的UI类
    matched_classes = find_main_city_ui_classes(json_file)
    
    if not matched_classes:
        print("\n❌ 未找到主城界面相关的UI类")
        return
    
    # 生成报告
    json_path, html_path = generate_main_city_report(matched_classes)
    
    print(f"\n✅ 主城界面可点击元素查找完成!")
    print(f"   找到 {len(matched_classes)} 个可能的主城UI类")
    print(f"   可点击元素总数: {sum(len(r['clickable_elements']) for r in matched_classes)} 个")
    print(f"   报告: {html_path}")
    
    # 显示第一个UI类的详细信息
    if matched_classes:
        print("\n" + "=" * 80)
        print("第一个UI类的详细信息:")
        display_ui_class_details(matched_classes[0])

if __name__ == "__main__":
    main()

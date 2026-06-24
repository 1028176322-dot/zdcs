#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from AutoSmoke.path_utils import as_abs_path
Poco Unity - ?"""

import sys
import time
import json

def test_poco_connection():
    """Poco"""
    print("=" * 80)
    print("Poco Unity - ?)
    print("=" * 80)
    
    try:
        # airtest
        print("\nairtest...")
        from airtest.core.api import connect_device
        
        # connect_device
        print("  connect_device('Windows://')...")
        device = connect_device('Windows://')
        print(f"  ?: {device}")
        
        # poco
        print("\npoco...")
        from poco.drivers.unity3d import UnityPoco
        
        # UnityPoco
        print("UnityPoco...")
        poco = UnityPoco()
        
        # Poco?        print("Poco?..")
        time.sleep(2)
        
        # ?        print("\n?..")
        
        # 1: ?        print("  1: ?..")
        try:
            clickable_elements_poco = poco('//*[@clickable=true]')
            clickable_count = len(clickable_elements_poco)
            print(f"    ? {clickable_count} ")
            
            # ?            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = as_abs_path("reports/runtime_capture/clickable_elements_{timestamp}.json")
            
            clickable_data = []
            for i, element in enumerate(clickable_elements_poco):
                element_data = {
                    "index": i,
                    "name": element.attr('name'),
                    "type": element.attr('type'),
                    "text": element.attr('text'),
                    "clickable": element.attr('clickable'),
                    "enabled": element.attr('enabled'),
                    "visible": element.attr('visible')
                }
                clickable_data.append(element_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(clickable_data, f, ensure_ascii=False, indent=2)
            
            print(f"  ?? {output_file}")
            print(f"\n  ? {clickable_count} :")
            for i, element in enumerate(clickable_data[:20]):  # 20?                print(f"    {i+1}. {element['name']} ({element['type']}) - {element['text']}")
            
            if clickable_count > 20:
                print(f"    ...  {clickable_count - 20} ?)
            
            return True
            
        except Exception as e1:
            print(f"  ?1: {e1}")
            
            # 2: utton?            print("  2: utton?..")
            try:
                button_elements = poco('//*[@type="Button"]')
                button_count = len(button_elements)
                print(f"    ? {button_count} utton")
                
                # ?                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = as_abs_path("reports/runtime_capture/button_elements_{timestamp}.json")
                
                button_data = []
                for i, element in enumerate(button_elements):
                    element_data = {
                        "index": i,
                        "name": element.attr('name'),
                        "type": element.attr('type'),
                        "text": element.attr('text'),
                        "clickable": element.attr('clickable'),
                        "enabled": element.attr('enabled'),
                        "visible": element.attr('visible')
                    }
                    button_data.append(element_data)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(button_data, f, ensure_ascii=False, indent=2)
                
                print(f"  ?Button: {output_file}")
                print(f"\n  ? {button_count} utton:")
                for i, element in enumerate(button_data[:20]):  # 20?                    print(f"    {i+1}. {element['name']} ({element['type']}) - {element['text']}")
                
                if button_count > 20:
                    print(f"    ...  {button_count - 20} ?)
                
                return True
                
            except Exception as e2:
                print(f"  ?2: {e2}")
                print("  ??)
                return False
        
    except Exception as e:
        print(f"\n?: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_poco_connection()



"""
UI树处理器模块
按照方案文档4.2节的接口定义实现
包含Python侧文本修复算法（方案4.2.3节）

修复：正确读取payload中的字段（text、name、type等）
"""

import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple


class UITreeProcessor:
    """
    UI树处理器
    解析UI树，提取所有UI元素的文本、属性，识别可点击元素
    """
    
    # 可能包含文本的节点名称（按优先级排序）
    TEXT_NODE_NAMES = ['TxtDesc', 'Text', 'Label', 'DescText', 'Title', 'Name']
    
    def __init__(self, ui_tree: Dict):
        """
        初始化UI树处理器
        :param ui_tree: UI树（dict），由poco.dump()返回
        """
        # 规范化UI树（将payload中的字段提升到顶层）
        self.ui_tree = self._normalize_ui_tree(ui_tree)
        self.nodes_by_id = {}  # 用于快速查找节点
        self._build_node_index()
    
    def _normalize_ui_tree(self, node, depth=0):
        """
        规范化UI树：将payload中的字段提升到顶层
        Poco dump的格式是：{name, payload: {name, type, text, ...}, children}
        但我们的代码期望的是：{name, type, text, ... children}
        所以需要规范化
        """
        if not node or not isinstance(node, dict):
            return node
        
        # 创建新节点（复制payload中的字段到顶层）
        new_node = dict(node)  # 先复制顶层字段
        
        # 将payload中的字段提升到顶层
        payload = node.get('payload')
        if payload and isinstance(payload, dict):
            for key, value in payload.items():
                new_node[key] = value
        
        # 删除payload字段（可选，为了清晰）
        if 'payload' in new_node:
            del new_node['payload']
        
        # 递归处理子节点
        if 'children' in new_node:
            new_node['children'] = [
                self._normalize_ui_tree(child, depth + 1)
                for child in new_node.get('children', [])
            ]
        
        return new_node
    
    def _build_node_index(self):
        """构建节点索引（按name字段）"""
        if not self.ui_tree:
            return
        
        def traverse(node, parent=None):
            if not node or not isinstance(node, dict):
                return
            
            # 设置父节点引用
            if parent:
                node['parent'] = parent
            
            # 索引节点
            name = node.get('name', '')
            if name:
                if name not in self.nodes_by_id:
                    self.nodes_by_id[name] = []
                self.nodes_by_id[name].append(node)
            
            # 递归处理子节点
            for child in node.get('children', []):
                traverse(child, node)
        
        traverse(self.ui_tree)
    
    def extract_all_texts(self) -> List[str]:
        """
        提取所有文本内容
        :return: 文本列表（去重）
        """
        texts = set()
        
        def traverse(node):
            if not node or not isinstance(node, dict):
                return
            
            # 提取当前节点的text（现在在顶层，不在payload中）
            text = node.get('text', '')
            if text and isinstance(text, str) and text.strip():
                texts.add(text.strip())
            
            # 递归处理子节点
            for child in node.get('children', []):
                traverse(child)
        
        traverse(self.ui_tree)
        return list(texts)
    
    def find_clickable_elements(self, smart_mode: bool = True) -> List[Dict]:
        """
        查找所有可点击元素（智能模式 - 合并严格条件和宽松条件）
        :param smart_mode: 是否启用智能模式（默认True）
        :return: 可点击元素列表
        """
        clickable_elements = []
        
        # 智能模式：合并严格条件和宽松条件
        if smart_mode:
            # 方法1：严格条件（最可靠）
            def traverse_strict(node):
                if not node or not isinstance(node, dict):
                    return
                
                is_clickable = node.get('clickable', False)
                node_type = node.get('type', '')
                
                # 严格条件
                if is_clickable:
                    clickable_elements.append(node)
                elif node_type in ['Button', 'Toggle', 'Slider', 'ScrollBar', 'InputField']:
                    clickable_elements.append(node)
                
                # 递归处理子节点
                for child in node.get('children', []):
                    traverse_strict(child)
            
            traverse_strict(self.ui_tree)
            
            # 方法2：宽松条件（补充潜在的可点击元素）
            # 即使严格条件找到了一些元素，仍然使用宽松条件补充
            loose_elements = self._find_clickable_elements_loose()
            
            # 合并（去重）
            seen = set()
            for elem in clickable_elements:
                name = elem.get('name', '')
                seen.add(name)
            
            for elem in loose_elements:
                name = elem.get('name', '')
                if name not in seen:
                    seen.add(name)
                    clickable_elements.append(elem)
        
        # 非智能模式：直接使用宽松条件
        else:
            clickable_elements = self._find_clickable_elements_loose()
        
        # 去重（根据name）
        seen = set()
        unique_elements = []
        for elem in clickable_elements:
            name = elem.get('name', '')
            if name not in seen:
                seen.add(name)
                unique_elements.append(elem)
        
        return unique_elements
    
    def _find_clickable_elements_loose(self) -> List[Dict]:
        """
        宽松条件：根据节点名称判断是否为可点击元素
        注意：可能会误判，但能找到更多潜在的可点击元素
        """
        clickable_elements = []
        
        # 排除的节点名称模式（明显的非按钮节点）
        exclude_patterns = [
            'TipNode_',        # 提示节点
            '_Normal(Clone)',   # 正常建筑节点
            '_LevelUpRewardBubble_',  # 升级奖励气泡
            'AudioObject-',     # 音频对象
            'Plot_',           # 剧情对象
            'Timeline',         # 时间线
            'Actor',           # 角色
            'Ship',            # 船只
            'Building',        # 建筑
            'GameObject',       # 游戏对象
        ]
        
        # 严格的名称匹配规则（减少误判）
        # 只识别名称以特定后缀结尾的节点
        STRICT_SUFFIXES = [
            'Button',          # 按钮
            'Btn',             # 按钮
            'Item',            # 列表项
            'Cell',            # 列表项
            'Tab',             # 标签页
            'Icon',            # 图标按钮
            'ClickContent',     # 点击内容
        ]
        
        def should_exclude(name: str) -> bool:
            """检查节点是否应该被排除"""
            return any(pattern in name for pattern in exclude_patterns)
        
        def traverse(node):
            if not node or not isinstance(node, dict):
                return
            
            name = node.get('name', '')
            
            # 排除明显的非按钮节点
            if should_exclude(name):
                # 递归处理子节点
                for child in node.get('children', []):
                    traverse(child)
                return
            
            # 严格的名称匹配（只识别以特定后缀结尾的节点）
            if any(name.endswith(suffix) for suffix in STRICT_SUFFIXES):
                clickable_elements.append(node)
            
            # 递归处理子节点
            for child in node.get('children', []):
                traverse(child)
        
        traverse(self.ui_tree)
        return clickable_elements
    
    def find_element_by_text(self, text: str) -> Optional[Dict]:
        """
        根据文本查找元素
        :param text: 文本（支持模糊匹配）
        :return: 元素节点，未找到返回None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        def traverse(node):
            if not node or not isinstance(node, dict):
                return None
            
            # 检查当前节点的text
            node_text = node.get('text', '')
            if node_text and isinstance(node_text, str) and text_lower in node_text.lower():
                return node
            
            # 递归处理子节点
            for child in node.get('children', []):
                result = traverse(child)
                if result:
                    return result
            
            return None
        
        return traverse(self.ui_tree)
    
    def generate_page_fingerprint(self) -> str:
        """
        生成页面指纹（基于UI树特征）
        用于判断是否为同一页面，避免重复访问
        :return: 指纹字符串 (MD5)
        """
        if not self.ui_tree:
            return ''
        
        # 使用UI树中可点击元素的名称和位置生成指纹
        features = []
        
        def traverse(node, depth=0):
            if not node or not isinstance(node, dict) or depth > 10:
                return
            
            name = node.get('name', '')
            pos = node.get('pos', [])
            
            # 只使用可点击元素
            clickable_names = ['Button', 'ClickContent', 'Item', 'Cell']
            is_clickable = node.get('clickable', False)
            
            if any(cn in name for cn in clickable_names) or is_clickable:
                # 使用名称+位置作为特征
                feature = f"{name}:{pos}"
                features.append(feature)
            
            # 递归处理子节点
            for child in node.get('children', []):
                traverse(child, depth + 1)
        
        traverse(self.ui_tree)
        
        # 排序后生成MD5
        features.sort()
        feature_str = '|'.join(features)
        
        return hashlib.md5(feature_str.encode('utf-8')).hexdigest()
    
    def fix_clickcontent_text(self, node: Dict, max_depth: int = 10) -> str:
        """
        修复ClickContent节点的文本提取问题（Python侧修复）
        这是方案文档4.2.3节提到的算法实现
        
        :param node: ClickContent节点
        :param max_depth: 最大搜索深度（向上查找祖先节点的层数）
        :return: 修复后的文本
        """
        if not node or not isinstance(node, dict):
            return ''
        
        name = node.get('name', '')
        
        # 只处理ClickContent节点
        if 'ClickContent' not in name:
            return node.get('text', '')
        
        # 1. 首先检查自身text字段
        text = node.get('text', '')
        if text and isinstance(text, str) and text.strip():
            return text.strip()
        
        # 2. 查找兄弟节点中的文本
        sibling_text = self._find_text_in_siblings(node)
        if sibling_text:
            return sibling_text
        
        # 3. 查找祖先节点的子节点中的文本
        ancestor_text = self._find_text_in_ancestors(node, max_depth)
        if ancestor_text:
            return ancestor_text
        
        # 4. 未找到文本
        return ''
    
    def _find_text_in_siblings(self, node: Dict) -> str:
        """查找兄弟节点中的文本（如TxtDesc）"""
        parent = node.get('parent')
        if not parent or not isinstance(parent, dict):
            return ''
        
        # 在兄弟节点中查找文本
        for sibling in parent.get('children', []):
            if sibling is node:
                continue
            
            # 检查兄弟节点的text字段
            sibling_text = sibling.get('text', '')
            if sibling_text and isinstance(sibling_text, str) and sibling_text.strip():
                return sibling_text.strip()
            
            # 检查兄弟节点的子节点中的文本
            def find_text_in_children(n):
                if not isinstance(n, dict):
                    return ''
                
                text = n.get('text', '')
                if text and isinstance(text, str) and text.strip():
                    return text.strip()
                
                for child in n.get('children', []):
                    result = find_text_in_children(child)
                    if result:
                        return result
                
                return ''
            
            result = find_text_in_children(sibling)
            if result:
                return result
        
        return ''
    
    def _find_text_in_ancestors(self, node: Dict, max_depth: int) -> str:
        """向上查找祖先节点，在其子节点中查找文本"""
        current = node
        for _ in range(max_depth):
            if not current:
                break
            
            parent = current.get('parent')
            if not parent or not isinstance(parent, dict):
                break
            
            # 在祖先节点的子节点中查找文本
            for sibling in parent.get('children', []):
                if sibling is node:
                    continue
                
                # 检查兄弟节点的text字段
                sibling_text = sibling.get('text', '')
                if sibling_text and isinstance(sibling_text, str) and sibling_text.strip():
                    return sibling_text.strip()
                
                # 检查兄弟节点的子节点中的文本
                def find_text_in_children(n):
                    if not isinstance(n, dict):
                        return ''
                    
                    text = n.get('text', '')
                    if text and isinstance(text, str) and text.strip():
                        return text.strip()
                    
                    for child in n.get('children', []):
                        result = find_text_in_children(child)
                        if result:
                            return result
                    
                    return ''
                
                result = find_text_in_children(sibling)
                if result:
                    return result
            
            current = parent
        
        return ''
    
    def to_json(self, filename: Optional[str] = None) -> Optional[str]:
        """
        将UI树保存为JSON文件
        :param filename: 文件名（可选）
        :return: JSON字符串，失败返回None
        """
        if not self.ui_tree:
            return None
        
        try:
            # 创建UI树的副本（去除parent引用，避免循环引用）
            def remove_parent_refs(node):
                if not node or not isinstance(node, dict):
                    return node
                
                # 创建新节点（不包含parent）
                new_node = {k: v for k, v in node.items() if k != 'parent'}
                
                # 递归处理子节点
                if 'children' in new_node:
                    new_node['children'] = [remove_parent_refs(child) for child in new_node['children']]
                
                return new_node
            
            clean_tree = remove_parent_refs(self.ui_tree)
            json_str = json.dumps(clean_tree, ensure_ascii=False, indent=2)
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                print(f"✓ UI树已保存至: {filename}")
            
            return json_str
            
        except Exception as e:
            print(f"✗ 保存UI树失败: {e}")
            return None

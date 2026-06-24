# AutoSmoke - GameContent 统一坐标系统设计方案

## 1. 目标

将所有操作（截图、点击、OCR、模板匹配）的坐标基准从 `game_view_coords`（全面板）迁移到 `gameContentRect`（纯游戏画面），实现统一的坐标基座。

## 2. 坐标关系

```
游戏设计分辨率: 1170 x 2532 (归一化坐标 0-1)
        │
        │ × scale (0.272)
        ▼
gameContentRect: (85, 62, 403, 750)  318 x 688
        │
        │ + game_view_coords.left/top 偏移
        ▼
屏幕绝对坐标: (271+85, 51+62, 759+offset, ...)
        │
        │ 裁剪或截图
        ▼
game_content 纯截图: 318 x 688
```

## 3. 核心类设计

### GameContentCoordSystem

```python
class GameContentCoordSystem:
    """基于 gameContentRect 的统一坐标系统"""

    def __init__(self, config_path="config.json"):
        """从 config.json 读取 gameContentRect + game_view_coords"""

    # ====== 只读属性 ======
    content_rect  -> {left, top, width, height}     # gameContentRect
    scale         -> {x, y}                          # 缩放比例
    screen_offset -> {x, y}                          # 截图原点在屏幕上的偏移

    # ====== 坐标转换 ======
    def normalized_to_content(nx, ny) -> (sx, sy)
        """游戏归一化坐标(0-1) → gameContent 内像素坐标"""

    def game_pixel_to_content(gx, gy) -> (sx, sy)
        """游戏设计分辨率像素坐标 → gameContent 内像素坐标"""

    def content_to_screen(cx, cy) -> (sx, sy)
        """gameContent 内像素坐标 → 屏幕绝对坐标"""

    def normalized_to_screen(nx, ny) -> (sx, sy)
        """游戏归一化坐标 → 屏幕绝对坐标（一步到位）"""

    # ====== 截图 ======
    def capture_game_content() -> Image
        """截取全屏 → 裁剪出 gameContent 区域"""

    def crop_game_content(full_screenshot) -> Image
        """从已有截图中裁剪 gameContent 区域"""

    # ====== 点击 ======
    def click_screen(sx, sy)
        """基于 gameContent 坐标的屏幕点击（win32）"""

    def click_normalized(nx, ny)
        """归一化坐标点击"""

    def click_game_pixel(gx, gy)
        """游戏像素坐标点击"""

    # ====== OCR / 模板匹配 ======
    @property
    def ocr_region() -> (left, top, right, bottom)
        """OCR 识别区域"""

    def get_sub_region(norm_left, norm_top, norm_right, norm_bottom)
        """在 gameContent 内取子区域（归一化坐标指定）"""

    # ====== 调试 ======
    def draw_content_rect(image) -> Image
        """在图上画出 gameContentRect 标注框"""
```

## 4. 调用方式

```python
# 初始化（只需一次）
coord = GameContentCoordSystem()

# 截取纯游戏画面
game_img = coord.capture_game_content()     # 自动全屏截图+裁剪
game_img.save("game_content.png")

# 点击（归一化坐标 → 自动计算 → 模拟点击）
coord.click_normalized(0.5, 0.5)             # 点游戏画面中心
coord.click_normalized(0.3, 0.2)             # 点左上区域

# 点击（游戏设计分辨率坐标）
coord.click_game_pixel(585, 1266)            # 点游戏中心

# 获取 OCR 区域
region = coord.ocr_region                    # (85, 62, 403, 750)

# 获取 gameContent 内的子区域（用于模板匹配）
btn_region = coord.get_sub_region(0.1, 0.8, 0.9, 0.95)
```

## 5. 涉及修改的文件

| 文件 | 改动 |
|------|------|
| **新建** `core_engine/game_content_coord_system.py` | 核心坐标系统类 |
| **修改** `core_engine/extract_game_ui_elements.py` | `normalized_to_game_pixel()` 改用 gameContentRect |
| **修改** `core_engine/screen_recognizer.py` | 识别和点击改用新坐标系 |
| **修改** `core_engine/action_executor/action_executor.py` | 添加基于坐标的点击方法 |

## 6. 第一阶段实现内容

1. 创建 `GameContentCoordSystem` 类（含坐标转换 + 截图裁剪 + 点击）
2. 修改 `extract_game_ui_elements.py` 使用 gameContentRect
3. 编写测试脚本验证点击位置正确性

# AutoSmoke - 自动点击阻塞界面处理实施方案

## 1. 背景

在按用例步骤自动点击时，经常会出现以下情况：

```text
步骤 1 点击后打开了弹窗
步骤 2 预期点击原页面按钮
但当前界面已被弹窗、遮罩、引导、公告、奖励页面阻挡
```

如果执行器不做处理，继续执行下一步，会导致：

```text
误点弹窗按钮
点击落空
点击危险确认
用例误判失败
页面状态越来越偏离预期
报告无法复现问题
```

因此，自动点击执行器必须加入：

```text
界面状态确认
阻塞界面检测
安全处理策略
处理失败阻断
证据记录
```

## 2. 目标

本方案目标是实现：

```text
每一步点击后，自动判断当前界面是否阻碍下一步执行；
如果存在可安全处理的阻塞界面，则自动关闭或处理；
如果存在危险弹窗或无法处理的阻塞，则停止当前用例并输出 BLOCKED/FAIL。
```

最终效果：

```text
自动执行不是盲目连点，而是每一步都能确认界面状态，并安全进入下一步。
```

## 3. 设计边界

必须遵守当前项目约束：

```text
不修改游戏业务运行过程代码
允许使用 Unity Editor 辅助脚本读取只读信息
允许使用截图、OCR、模板匹配、Poco dump、日志分析
所有能力最终封装到 IDE
```

阻塞处理不能自动执行高风险确认操作。

高风险操作包括：

```text
充值
购买
消耗钻石
删除
解散
退出登录
确认支付
重置账号
使用稀有道具
```

## 4. 总体流程

在用例执行器中加入 `PostActionGuard`。

```text
执行当前步骤
-> 等待界面稳定
-> 采集当前截图/OCR/UI树/日志
-> 判断当前界面是否满足下一步前置条件
-> 如果满足，进入下一步
-> 如果不满足，检测是否存在阻塞界面
-> 如果是安全阻塞，自动处理
-> 处理后重新检测
-> 超过处理次数仍失败，标记 BLOCKED/FAIL
```

完整流程：

```text
case_step_executor
  -> execute_step()
  -> post_action_guard.check()
      -> ui_state_checker.check_next_precondition()
      -> blocker_detector.detect()
      -> blocker_resolver.resolve()
      -> evidence_collector.save()
  -> next_step / stop_case
```

## 5. 模块规划

建议新增以下模块：

```text
E:/zdcs/AutoSmoke/post_action_guard.py
E:/zdcs/AutoSmoke/blocker_detector.py
E:/zdcs/AutoSmoke/blocker_resolver.py
E:/zdcs/AutoSmoke/ui_state_checker.py
E:/zdcs/AutoSmoke/blocker_rules.py
```

### 5.1 post_action_guard.py

职责：

```text
每步执行后的统一守卫流程
判断是否可以进入下一步
调度 blocker_detector 和 blocker_resolver
控制最大处理次数
输出 guard_result
```

### 5.2 blocker_detector.py

职责：

```text
检测当前界面是否存在阻塞
识别阻塞类型
输出 blocker_result
```

检测来源：

```text
OCR 文本
模板匹配
截图差异
Poco dump
UI 树
日志
颜色/遮罩检测
```

### 5.3 blocker_resolver.py

职责：

```text
根据阻塞类型选择安全动作
执行关闭、取消、返回、等待、点击空白等动作
处理危险阻塞时直接阻断
```

### 5.4 ui_state_checker.py

职责：

```text
判断当前界面是否满足下一步前置条件
判断目标元素是否存在
判断页面是否处于可执行状态
```

### 5.5 blocker_rules.py

职责：

```text
维护阻塞规则
维护危险关键词
维护安全关闭动作优先级
维护不同项目的自定义规则
```

## 6. 阻塞类型定义

### 6.1 普通弹窗

特征：

```text
出现“确定 / 取消 / 关闭 / 关闭按钮 / X”
背景被遮罩
弹窗区域覆盖当前页面
弹窗主体外存在可点击空白区域
点击弹窗外空白区域可关闭弹窗
```

处理策略：

```text
优先点关闭 X
其次点取消
再点弹窗外安全空白区域
最后尝试返回
```

通用弹窗类型：

```text
blockerType = modal_popup
closeStrategy = close_button | cancel_button | outside_blank_area | press_back
```

适用场景：

```text
背景变暗的遮罩弹窗
红框区域有缺口的弹窗
点击弹窗外空白区域可关闭的游戏内通用弹窗
```

### 6.2 奖励弹窗

特征：

```text
出现“领取 / 获得 / 奖励 / 恭喜 / 点击继续”
出现“恭喜获得”
有物品图标或奖励列表
背景被遮罩
底部通常有“确认”按钮
```

处理策略：

```text
如果识别为奖励弹窗，点击“确认”属于安全动作
点击后验证“恭喜获得”消失
如果确认按钮找不到，尝试点击空白区域关闭
若奖励涉及确认消耗，则阻断
```

注意：

```text
奖励弹窗中的“确认”是白名单安全确认。
它不等同于购买、充值、消耗钻石等危险弹窗里的“确认”。
只有命中 reward_popup 规则时，才允许自动点击“确认”。
```

### 6.3 Loading 遮罩

特征：

```text
出现“加载中 / Loading / 转圈 / 请稍候”
画面变化小
用户操作被遮罩拦截
```

处理策略：

```text
等待
多次检查
超过 timeout 标记 BLOCKED_LOADING_TIMEOUT
```

### 6.3.1 场景跳转 Loading

特征：

```text
进入新的场景或玩法时出现专用 Loading 页面
有进度条，例如 54%
有加载文案，例如“升级灯塔以提升实力”
通常不是异常，也不应关闭
```

类型：

```text
blockerType = scene_transition_loading
```

处理策略：

```text
1. 等待进度条完成。
2. 周期性识别百分比是否增长。
3. 进度达到 100% 或 Loading 页面消失后继续下一步。
4. 如果进度长时间不变，标记 BLOCKED_SCENE_LOADING_STUCK。
5. 如果超过最大等待时间，标记 BLOCKED_SCENE_LOADING_TIMEOUT。
```

注意：

```text
场景跳转 Loading 是正常流程，不应点击关闭、取消、空白区域或返回。
```

### 6.4 新手引导

特征：

```text
出现高亮区域
大面积半透明遮罩
出现“下一步 / 跳过 / 点击这里”
出现手指图标
出现红框/高亮框指向需要点击的位置
其它区域被遮罩或不可交互
```

处理策略：

```text
优先点击跳过
若无跳过，则按引导规则点击高亮区域或手指指向点
无法处理则 BLOCKED_GUIDE
```

引导类型：

```text
blockerType = guide_overlay
resolveStrategy = click_skip | click_highlight_area | click_finger_target | wait_manual
```

注意：

```text
引导界面不能按普通弹窗处理。
不要点击弹窗外空白区域。
不要随意点击底部按钮栏。
应只点击引导明确指向的区域。
```

### 6.5 系统公告

特征：

```text
出现“公告 / 活动 / 更新 / 今日提示”
通常有关闭按钮
```

处理策略：

```text
点击关闭
如果无关闭，尝试返回
```

### 6.6 网络/重连弹窗

特征：

```text
断线重连
网络异常
重新连接
重试
正在连接
正在重连
转圈 Loading
```

处理策略：

```text
优先等待恢复
如果出现“重试/重新连接”，可按规则点击重试
超过次数后标记 BLOCKED_NETWORK
```

### 6.6.1 调试面板中的重连/Loading

部分项目会在调试面板或 GM 面板中出现转圈状态，例如：

```text
弹窗仍在前台
中心区域出现 Loading 转圈
没有明确的“重试”按钮
当前页面无法继续执行下一步
```

该类情况归类为：

```text
blockerType = reconnect_loading
```

处理策略：

```text
1. 不点击面板内未知按钮。
2. 先等待固定时间，例如 3~10 秒。
3. 周期性截图检测转圈是否消失。
4. 如果弹窗有关闭按钮，等待超时后可尝试关闭。
5. 如果关闭后会影响用例前置状态，则标记 BLOCKED_RECONNECT_LOADING。
6. 超过最大等待时间仍存在，当前用例 BLOCKED。
```

注意：

```text
调试面板中按钮密集，不能随意点击空白或未知按钮。
该类界面优先等待，不优先自动操作。
```

### 6.7 危险确认弹窗

特征：

```text
充值
购买
消耗
钻石
删除
解散
退出登录
确认支付
```

处理策略：

```text
不点击确定
优先点击取消/关闭
如果无法关闭，标记 BLOCKED_DANGEROUS_ACTION
```

## 7. 阻塞检测规则

### 7.1 OCR 关键词检测

示例：

```json
{
  "type": "popup",
  "keywords": ["确定", "取消", "关闭"],
  "confidence": "medium"
}
```

奖励弹窗处理示例：

```json
{
  "stepIndex": 3,
  "guardStatus": "READY",
  "blockerType": "reward_popup",
  "keywords": ["恭喜获得"],
  "actionTaken": "click_reward_confirm",
  "result": "OK",
  "verify": "reward_popup_disappeared",
  "evidence": {
    "before": "reward_popup_before.png",
    "after": "reward_popup_after.png"
  }
}
```

重连等待示例：

```json
{
  "stepIndex": 4,
  "guardStatus": "BLOCKED_RECONNECT_LOADING",
  "blockerType": "reconnect_loading",
  "actionTaken": "wait",
  "waitMs": 10000,
  "result": "BLOCKED",
  "message": "重连 Loading 超时未消失",
  "evidence": {
    "screenshot": "reconnect_loading_timeout.png"
  }
}
```

场景跳转 Loading 示例：

```json
{
  "stepIndex": 6,
  "guardStatus": "READY",
  "blockerType": "scene_transition_loading",
  "actionTaken": "wait_until_progress_complete",
  "progressStart": 54,
  "progressEnd": 100,
  "waitMs": 8200,
  "result": "OK",
  "message": "场景加载完成，继续下一步",
  "evidence": {
    "before": "scene_loading_54.png",
    "after": "scene_loaded.png"
  }
}
```

场景加载卡住示例：

```json
{
  "stepIndex": 6,
  "guardStatus": "BLOCKED_SCENE_LOADING_STUCK",
  "blockerType": "scene_transition_loading",
  "progress": 54,
  "stuckMs": 10000,
  "result": "BLOCKED",
  "message": "场景 Loading 进度长时间无变化",
  "evidence": {
    "screenshot": "scene_loading_stuck.png"
  }
}
```

新手引导处理示例：

```json
{
  "stepIndex": 5,
  "guardStatus": "READY",
  "blockerType": "guide_overlay",
  "actionTaken": "click_guide_target",
  "target": {
    "type": "finger_target",
    "point": [194, 408]
  },
  "result": "OK",
  "verify": "guide_target_changed",
  "evidence": {
    "before": "guide_before.png",
    "after": "guide_after.png"
  }
}
```

危险关键词：

```json
{
  "type": "dangerous_confirm",
  "keywords": ["充值", "购买", "钻石", "删除", "解散", "支付"],
  "confidence": "high"
}
```

### 7.2 模板匹配检测

常用模板：

```text
close_x.png
confirm_button.png
cancel_button.png
loading_spinner.png
scene_loading_progress_bar.png
guide_mask.png
guide_finger.png
guide_highlight_rect.png
reward_popup.png
reward_confirm_button.png
reconnect_spinner.png
```

### 7.3 UI 树/Poco 检测

如果 UI 树可用：

```text
检测 popup/dialog/panel
检测 close/cancel/confirm 节点
检测遮罩节点
检测可点击对象层级是否发生变化
```

### 7.4 截图特征检测

适用于 UI 树不可用时：

```text
大面积半透明遮罩
中央矩形弹窗
Loading 动画区域
页面突然变暗
目标区域被覆盖
```

## 8. 阻塞处理优先级

安全处理顺序：

```text
1. 检查危险关键词
2. 如果危险，禁止点确定
3. 优先点击关闭 X
4. 其次点击取消
5. 再点击弹窗外安全空白区域关闭
6. 再尝试返回
7. Loading 则等待
8. 超过次数后 BLOCKED
```

危险弹窗处理规则：

```text
如果存在危险关键词 + 确认按钮：
    不点击确认
    尝试取消/关闭
    如果无法取消/关闭：
        BLOCKED_DANGEROUS_ACTION
```

### 8.1 弹窗外空白区域关闭策略

很多游戏内通用弹窗支持点击弹窗外空白区域关闭。  
该能力应作为普通弹窗的安全关闭兜底策略。

触发条件：

```text
1. 检测到遮罩层或背景变暗。
2. 检测到弹窗主体矩形 popupRect。
3. 弹窗不是危险确认弹窗。
4. 弹窗外存在可点击空白区域。
5. 空白点击点不落在底部按钮、返回按钮、Debug 按钮或其它危险区域上。
```

安全空白点候选：

```text
left_bottom:
  x = popupRect.left + 20
  y = popupRect.bottom + 10

right_bottom:
  x = popupRect.right - 20
  y = popupRect.bottom + 10

top_left:
  x = popupRect.left + 20
  y = popupRect.top - 10

left_side:
  x = popupRect.left - 10
  y = popupRect.top + 20

right_side:
  x = popupRect.right + 10
  y = popupRect.top + 20
```

候选点必须满足：

```text
在 gameContentRect 内
不在 popupRect 内
不在危险区域内
不在底部按钮栏内
不在 Debug/返回按钮区域内
不在已识别出的可点击业务按钮上
```

推荐处理顺序：

```text
1. click_close_button
2. click_cancel_button
3. click_outside_blank_area
4. press_back
5. BLOCKED_POPUP_UNRESOLVED
```

关闭成功验证：

```text
1. 弹窗标题消失，例如“获取更多”消失。
2. 遮罩消失或画面亮度恢复。
3. popupRect 区域不再存在。
4. 下一步目标出现。
5. OCR/模板/UI树不再检测到该弹窗。
```

如果空白点击后弹窗仍存在：

```text
1. 尝试下一个候选空白点。
2. 达到最大尝试次数后，尝试 press_back。
3. 仍失败则 BLOCKED_POPUP_UNRESOLVED。
```

## 9. 下一步前置状态确认

每一步执行前，应该知道下一步需要什么状态。

示例：

```text
步骤 1：点击 背包道具
期望：出现 使用按钮

步骤 2：点击 text("使用")
前置：text("使用") 存在
```

执行步骤 2 前：

```text
先检查 text("使用") 是否存在
如果不存在，调用 blocker_detector
处理阻塞后再检查
仍不存在，则步骤 2 FAIL
```

## 10. PostActionGuard 伪代码

```python
class PostActionGuard:
    def __init__(self, detector, resolver, state_checker, max_attempts=3):
        self.detector = detector
        self.resolver = resolver
        self.state_checker = state_checker
        self.max_attempts = max_attempts

    def guard_before_next_step(self, next_step):
        for attempt in range(self.max_attempts):
            state_ok = self.state_checker.check_precondition(next_step)
            if state_ok:
                return {
                    "status": "READY",
                    "attempts": attempt
                }

            blocker = self.detector.detect()
            if not blocker:
                return {
                    "status": "NOT_READY",
                    "reason": "next step precondition not met and no blocker detected"
                }

            if blocker["dangerous"]:
                return {
                    "status": "BLOCKED_DANGEROUS_ACTION",
                    "blocker": blocker
                }

            resolved = self.resolver.resolve(blocker)
            if not resolved:
                return {
                    "status": "BLOCKED_UNRESOLVED",
                    "blocker": blocker
                }

        return {
            "status": "BLOCKED_MAX_ATTEMPTS",
            "attempts": self.max_attempts
        }
```

## 11. blocker_result 数据结构

```json
{
  "detected": true,
  "blockerType": "popup",
  "confidence": "high",
  "source": ["ocr", "template"],
  "keywords": ["确定", "取消"],
  "dangerous": false,
  "suggestedActions": ["click_close", "click_cancel", "press_back"],
  "screenshot": "runs/run_x/screenshots/blocker_001.png"
}
```

通用遮罩弹窗：

```json
{
  "detected": true,
  "blockerType": "modal_popup",
  "confidence": "high",
  "source": ["mask", "popup_rect", "ocr"],
  "title": "获取更多",
  "dangerous": false,
  "popupRect": [18, 176, 313, 518],
  "suggestedActions": [
    "click_close",
    "click_cancel",
    "click_outside_blank_area",
    "press_back"
  ],
  "outsideBlankCandidates": [
    [38, 528],
    [293, 528],
    [38, 166]
  ]
}
```

危险阻塞：

```json
{
  "detected": true,
  "blockerType": "dangerous_confirm",
  "confidence": "high",
  "keywords": ["钻石", "购买"],
  "dangerous": true,
  "suggestedActions": ["click_cancel", "click_close"],
  "forbiddenActions": ["click_confirm"]
}
```

奖励弹窗：

```json
{
  "detected": true,
  "blockerType": "reward_popup",
  "confidence": "high",
  "source": ["ocr", "template", "mask"],
  "keywords": ["恭喜获得", "获得", "奖励"],
  "dangerous": false,
  "safeConfirmAllowed": true,
  "suggestedActions": [
    "click_reward_confirm",
    "click_outside_blank_area"
  ],
  "verifyDisappearText": ["恭喜获得", "确认"]
}
```

重连 Loading：

```json
{
  "detected": true,
  "blockerType": "reconnect_loading",
  "confidence": "high",
  "source": ["template", "screenshot"],
  "keywords": ["正在重连", "重新连接", "网络异常"],
  "dangerous": false,
  "suggestedActions": [
    "wait",
    "click_retry_if_visible",
    "click_close_if_timeout"
  ],
  "maxWaitMs": 10000
}
```

场景跳转 Loading：

```json
{
  "detected": true,
  "blockerType": "scene_transition_loading",
  "confidence": "high",
  "source": ["progress_bar", "ocr", "screenshot"],
  "dangerous": false,
  "progress": 54,
  "text": "升级灯塔以提升实力",
  "suggestedActions": [
    "wait_until_progress_complete"
  ],
  "maxWaitMs": 30000,
  "stuckThresholdMs": 10000
}
```

新手引导：

```json
{
  "detected": true,
  "blockerType": "guide_overlay",
  "confidence": "high",
  "source": ["template", "highlight_rect", "screenshot"],
  "dangerous": false,
  "guideTarget": {
    "type": "finger_target",
    "rect": [122, 327, 266, 490],
    "center": [194, 408]
  },
  "suggestedActions": [
    "click_skip_if_visible",
    "click_guide_target",
    "wait_manual"
  ],
  "maxSteps": 5
}
```

空白区域关闭示例：

```json
{
  "status": "READY",
  "attempts": 1,
  "handledBlockers": [
    {
      "blockerType": "modal_popup",
      "action": "click_outside_blank_area",
      "point": [38, 528],
      "verify": "popup_title_disappeared",
      "result": "OK"
    }
  ],
  "beforeScreenshot": "...",
  "afterScreenshot": "..."
}
```

## 12. guard_result 数据结构

```json
{
  "status": "READY",
  "attempts": 1,
  "handledBlockers": [
    {
      "blockerType": "popup",
      "action": "click_close",
      "result": "OK"
    }
  ],
  "beforeScreenshot": "...",
  "afterScreenshot": "..."
}
```

失败示例：

```json
{
  "status": "BLOCKED_DANGEROUS_ACTION",
  "blocker": {
    "blockerType": "dangerous_confirm",
    "keywords": ["钻石", "购买"]
  },
  "message": "检测到危险确认弹窗，禁止自动点击确定"
}
```

## 13. 与用例执行器集成

执行器流程调整为：

```text
执行 step[i]
-> 生成 step_result
-> 如果还有 step[i+1]
   -> PostActionGuard 检查是否可进入下一步
   -> READY：继续
   -> BLOCKED/FAIL：终止当前用例
```

如果当前步骤本身有明确期望结果：

```text
先判断当前步骤期望
再判断下一步前置
```

## 14. IDE 封装

IDE 中应展示：

```text
当前步骤
下一步前置条件
是否检测到阻塞
阻塞类型
危险等级
处理动作
处理结果
before/after 截图
阻塞处理日志
```

IDE 操作：

```text
启用/关闭自动处理阻塞
配置最大处理次数
配置危险关键词
配置允许自动关闭的弹窗类型
手动确认处理一次
查看阻塞截图
```

## 15. 配置建议

```json
{
  "post_action_guard": {
    "enabled": true,
    "max_attempts": 3,
    "wait_after_action_ms": 800,
    "blocker_timeout_ms": 10000,
    "auto_resolve_safe_popup": true,
    "auto_resolve_loading": true,
    "auto_resolve_reward_popup": true,
    "auto_resolve_reconnect_loading": true,
    "auto_resolve_guide": false,
    "danger_keywords": [
      "充值",
      "购买",
      "钻石",
      "支付",
      "删除",
      "解散",
      "退出登录"
    ],
    "safe_close_keywords": [
      "关闭",
      "取消",
      "返回",
      "稍后"
    ],
    "modal_popup": {
      "enable_click_outside_blank": true,
      "outside_blank_priority": 3,
      "verify_after_click": true,
      "outside_blank_offsets": [
        ["left_bottom", 20, 10],
        ["right_bottom", -20, 10],
        ["top_left", 20, -10],
        ["left_side", -10, 20],
        ["right_side", 10, 20]
      ],
      "safe_area_blacklist": [
        "bottom_action_bar",
        "debug_button",
        "back_button",
        "danger_buttons"
      ]
    },
    "reward_popup": {
      "enabled": true,
      "allow_click_confirm": true,
      "keywords": [
        "恭喜获得",
        "获得",
        "奖励",
        "领取成功"
      ],
      "confirm_keywords": [
        "确认"
      ],
      "verify_disappear_keywords": [
        "恭喜获得",
        "确认"
      ]
    },
    "reconnect_loading": {
      "enabled": true,
      "wait_interval_ms": 1000,
      "max_wait_ms": 10000,
      "allow_click_retry": true,
      "allow_close_after_timeout": true,
      "keywords": [
        "正在重连",
        "重新连接",
        "网络异常",
        "重试"
      ]
    },
    "scene_transition_loading": {
      "enabled": true,
      "wait_interval_ms": 1000,
      "max_wait_ms": 30000,
      "stuck_threshold_ms": 10000,
      "progress_keywords": [
        "%",
        "Loading",
        "加载"
      ],
      "known_texts": [
        "升级灯塔以提升实力"
      ],
      "forbidden_actions": [
        "click_close",
        "click_cancel",
        "click_outside_blank_area",
        "press_back"
      ]
    },
    "guide_overlay": {
      "enabled": true,
      "auto_resolve": true,
      "prefer_skip": true,
      "allow_click_highlight_area": true,
      "allow_click_finger_target": true,
      "max_guide_steps": 5,
      "templates": [
        "guide_finger.png",
        "guide_highlight_rect.png",
        "guide_skip_button.png"
      ],
      "forbidden_actions": [
        "click_outside_blank_area",
        "click_random_area"
      ]
    }
  }
}
```

## 16. 报告体现

报告中应记录：

```text
是否出现阻塞
阻塞类型
识别来源
是否自动处理
处理动作
处理是否成功
是否阻断用例
相关截图
```

示例：

```json
{
  "stepIndex": 2,
  "guardStatus": "BLOCKED_DANGEROUS_ACTION",
  "blockerType": "dangerous_confirm",
  "keywords": ["钻石", "购买"],
  "actionTaken": "none",
  "result": "BLOCKED",
  "evidence": {
    "screenshot": "blocker_002.png",
    "ocr": "ocr_002.json"
  }
}
```

## 17. 验收标准

### 17.1 普通弹窗处理

```text
点击后出现普通弹窗
系统能识别弹窗
能点击关闭/取消
关闭/取消失败时能点击弹窗外安全空白区域
关闭后进入下一步
报告记录处理过程
```

### 17.2 弹窗外空白区域关闭

```text
出现带遮罩的通用弹窗
系统能识别 popupRect
系统能计算至少 1 个安全空白点
点击空白点后弹窗关闭
关闭后验证弹窗标题/遮罩消失
点击点不能落在底部按钮、Debug、返回按钮或危险按钮上
报告记录 click_outside_blank_area 的点击点和验证结果
```

### 17.3 Loading 处理

```text
出现 Loading 时不立即失败
在超时时间内等待
Loading 消失后继续
超时后标记 BLOCKED_LOADING_TIMEOUT
```

### 17.4 场景跳转 Loading 处理

```text
出现带进度条的场景跳转 Loading
系统识别 scene_transition_loading
不点击关闭、取消、空白区域或返回
能读取或估算进度条百分比
进度完成或 Loading 消失后继续下一步
进度长时间不变时标记 BLOCKED_SCENE_LOADING_STUCK
超过最大等待时间时标记 BLOCKED_SCENE_LOADING_TIMEOUT
报告记录 progressStart/progressEnd/waitMs
```

### 17.5 奖励弹窗处理

```text
出现“恭喜获得”奖励弹窗
系统能识别 reward_popup
系统允许点击奖励弹窗中的“确认”
点击后验证“恭喜获得”消失
如果确认按钮找不到，可尝试弹窗外空白区域关闭
报告记录 reward_popup 和 click_reward_confirm
```

### 17.6 重连 Loading 处理

```text
出现正在重连或转圈 Loading
系统识别 reconnect_loading
优先等待，不随意点击未知按钮
Loading 消失后继续下一步
超时后标记 BLOCKED_RECONNECT_LOADING
报告记录等待时长和超时截图
```

### 17.7 新手引导处理

```text
出现手指图标或高亮引导框
系统识别 guide_overlay
优先点击“跳过”（如果存在且规则允许）
无跳过时点击手指指向点或高亮区域中心
不允许点击弹窗外空白区域
连续引导超过 max_guide_steps 后标记 BLOCKED_GUIDE
报告记录每次引导点击点和前后截图
```

### 17.8 危险弹窗处理

```text
出现“购买/钻石/支付”等危险弹窗
系统不点击确认
优先尝试关闭/取消
无法处理时 BLOCKED_DANGEROUS_ACTION
```

### 17.9 下一步前置检查

```text
下一步目标不存在时不盲目点击
先尝试处理阻塞
处理后仍不存在则 FAIL/BLOCKED
```

### 17.10 IDE 验收

```text
IDE 能显示阻塞类型
IDE 能显示处理动作
IDE 能查看阻塞截图
IDE 能配置是否自动处理阻塞
IDE 能显示 click_outside_blank_area 候选点
IDE 能区分 reward_popup 的安全确认和 dangerous_confirm 的危险确认
IDE 能显示 reconnect_loading 的等待时长和超时状态
IDE 能显示 guide_overlay 的高亮区域、手指目标点和已处理步数
IDE 能显示 scene_transition_loading 的进度、等待时长和卡住状态
```

## 18. 实施优先级

```text
1. ui_state_checker.py
2. blocker_rules.py
3. blocker_detector.py（先 OCR + 模板）
4. blocker_resolver.py（关闭/取消/返回/等待）
5. post_action_guard.py
6. case_step_executor 集成
7. 报告记录
8. IDE 配置和可视化
```

## 19. 结论

自动点击打开其它界面并不是异常情况，而是游戏 UI 自动化中的常态。

正确处理方式是：

```text
每步后检查状态
下一步前确认前置
安全弹窗自动处理
危险弹窗坚决阻断
处理过程留证据
结果写入报告
```

完成该能力后，AutoSmoke 的用例执行会从"按步骤点"升级为"按状态安全推进"，这也是后续全功能 IDE 化的关键能力。

---

## 20. 实施完成总结（2026-06-12）

### 20.1 交付物（8 步全部完成 ✅）

| 实施优先级 | 模块 | 文件 | 状态 |
|:---------:|------|------|:----:|
| 1 | 界面状态检查器 | `ui_state_checker.py` | ✅ |
| 2 | 阻塞规则配置 | `blocker_rules.py` | ✅ |
| 3 | 阻塞检测器（OCR+模板+遮罩特征） | `blocker_detector.py` | ✅ |
| 4 | 阻塞处理器（关闭/取消/空白区/返回） | `blocker_resolver.py` | ✅ |
| 5 | 执行后守卫编排 | `post_action_guard.py` | ✅ |
| 6 | case_step_executor 集成 | — | ✅ 已集成 |
| 7 | 报告记录 | — | ✅ guard_result 含处理记录 |
| 8 | IDE 配置和可视化 | — | ⏳ 后续 IDE 面板扩展 |

### 20.2 支持阻塞类型

| 类型 | 检测方式 | 处理策略 | 状态 |
|------|----------|----------|:----:|
| 普通弹窗 | OCR关键词 + 遮罩特征 | 关闭→取消→空白区→返回 | ✅ |
| 遮罩弹窗 (modal_popup) | 截图亮度分析 + 弹窗矩形 | 空白候选点计算+点击 | ✅ |
| 奖励弹窗 | OCR:"恭喜获得/奖励/领取" | 点确认（白名单安全） | ✅ |
| Loading 遮罩 | OCR:"加载中/Loading" | 等待超时 | ✅ |
| 场景跳转 Loading | OCR:"%/加载中" | 等待进度完成 | ✅（接口） |
| 重连弹窗 | OCR:"正在重连/网络异常" | 先等待→后重试→超时阻断 | ✅ |
| 新手引导 | OCR:"下一步/跳过" + 引导目标 | 点跳过→点引导目标 | ✅ |
| 系统公告 | OCR:"公告/活动/更新" | 点关闭→返回 | ✅ |
| **危险确认** | OCR:"充值/购买/钻石/支付" | **不点确认→点取消→阻断** | ✅ |
| 空白区域关闭 | 弹窗矩形 + 5个安全候选点 | 逐点尝试→验证关闭 | ✅ |

### 20.3 集成效果

```
执行步骤 → 步骤完成
  └─ PostActionGuard.guard_before_next_step(下一步)
     ├─ UIStateChecker 检查前置条件
     │   ├─ 满足 → READY，继续
     │   └─ 不满足 → BlockerDetector 检测
     │       ├─ 危险 → BLOCKED_DANGEROUS_ACTION
     │       ├─ 检测到阻塞 → BlockerResolver 处理
     │       │   ├─ 成功 → 重新检查前置
     │       │   └─ 失败 → BLOCKED_UNRESOLVED
     │       └─ 未检测到 → NOT_READY
     └─ 超过 max_attempts → BLOCKED_MAX_ATTEMPTS
```

### 20.4 待实施

```text
1. IDE 调试面板中增加阻塞处理可视化（阻塞类型/处理动作/截图）
2. 将 blocker_rules 的配置接入 debug_panel 的配置页面
3. 场景跳转 Loading 的进度条百分比 OCR 识别
4. 新手引导高亮区域/手指指向的模板图片收集
```

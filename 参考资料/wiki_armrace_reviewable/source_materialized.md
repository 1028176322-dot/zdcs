# 系统/军备竞赛

# 军备竞赛(Arms Race) · V1.0

> 三层关系: H活动_军备竞赛配置(运行时实现,5 sheet) ← 本页(设计意图) ← 58-军备竞赛.xlsx(策划案原文)。
> 文档版本: V1.2(2026-06-16), 未锁定。原 6 项待补已清零, 待评审后锁定。

## 一、一句话定位

军备竞赛是一个 7 天为一循环的长线积分玩法活动: 玩家每日参与, 完成多类养成任务获积分; 每 4 小时刷新一轮竞赛主题(共 7 阶段 x 6 轮), 按积分领取积分奖励 / 目标奖励, 并按每日积分总量与匹配池内玩家排名竞争排行奖励。

## 二、系统组成

| Sheet | 行数 | 职责 | 关键字段 |
|---|---:|---|---|
| CArmRaceStage | 42 | 赛程编排: 7 阶段 x 6 轮, 每轮 4 小时, 指定主题 | StageID / RoundID / Time / ArmsRaceKindID |
| CArmsRaceKind | 6 | 竞赛主题: 6 类主题, 任务集合, 推荐任务, banner | ClassDes / IncludeTask / Recommend / Banner |
| CArmsRaceTask | 53 | 任务定义: 完成条件, 积分, 图标 | ClassID / Count / Params / QuestDes / Point / Icon / Group |
| CArmsRaceReward | 206 | 三类奖励: 目标, 积分, 排行 | RewardID / Class / CompetitionRank / Stage / Point / PointsDemand / Reward |
| CArmsRaceRank | 12 | 匹配段位定义: 阶段段位 11 档 + 轮次段位 1 档 | Type / Rank |

活动内容 ContentID = 6001。活动调度走 H活动配置 CActvOnline。调度行: ID=2040100, Type=67, TriggerType=2, TriggerVal=1d, Reopen=1, TriggerRept=7d, Duration=7d, LevelVal=7, MailUseActvID=18000016。

## 三、匹配机制

### 3.1 功能开启

服务器达到指定开服天数后开启功能, 精确天数以 CActvOnline 实际配置为准。玩家参与条件由 CActvOnline.LevelVal 控制; CArmsRaceRank 控制匹配等级区间。文本和配置互证最低参与等级为灯塔 7 级。

### 3.2 跨服匹配分组

跨服匹配分组由全局表 CCrossServerGroup 控制。军备竞赛当前未在 CCrossServerGroup 配置正式跨服分组, 即当前无活动专属跨服分组规则。

### 3.3 匹配时间与池子规则

功能达开启条件后, 等服务器第二天 UTC 0 点开始匹配。只有在线玩家参与匹配; 未在线者上线后再入池。池子上限 20 人。优先补未满小组, 满员后开新池; 无可匹配玩家时池内仅玩家本人。每日 UTC 0 点结算前一日并开新一轮匹配。

### 3.4 匹配段位

Type 1 阶段段位用于积分奖励, 共 11 档: [7,9], [10,12], [13,14], [15,16], [17,18], [19,20], [21,22], [23,24], [25,26], [27,28], [29,30]。Type 2 轮次段位用于目标奖励, 1 档 [7,30]。

## 四、竞赛结构

1 循环 = 7 阶段, 每阶段 = 6 轮, 每轮持续 4 小时。第 1 阶段第 1 轮在功能开启当天 UTC 0 点开启; 第 7 阶段在功能开启后第 7 天 UTC 24 点结束。每轮在 UTC 0/4/8/12/16/20 切换主题。CArmRaceStage 共 42 行, 主题 id 1-6 乱序编排。

## 五、任务体系

### 5.1 六大主题

| KindID | 主题 key | 含义 | IncludeTask | Recommend |
|---:|---|---|---|---|
| 1 | ArmRace_text_2 | 英雄养成 | 101,102,701 | 102 |
| 2 | ArmRace_text_3 | 城市建设 | 201,202,701 | 202 |
| 3 | ArmRace_text_4 | 士兵提升 | 301,302-311,701 | 302-311 |
| 4 | ArmRace_text_5 | 科技研发 | 401,402,701 | 402 |
| 5 | ArmRace_text_6 | 船只养成 | 502,503,511-540,701 | 511-540 |
| 6 | ArmRace_text_7 | 无人机/神器 | 601,602,701 | 601 |

每主题都含通用任务 701(购买含宝石礼包, 30 积分)。士兵和船只主题使用分级任务。

### 5.2 任务定义

关键字段: ClassID 是通用任务类型 id, Count 与 Params 定义完成阈值和额外参数, Point 是完成 1 次给的积分, Group 控制折叠分组, Icon / QuestDes 控制图标和描述。

任务积分约束: 购买礼包获取宝石任务 701 不计入主题类型但可得积分; 只有通过购买礼包获取的宝石才能获取积分。

## 六、奖励体系

三类奖励由 RewardID 区分。CompetitionRank 字段语义随 RewardID 变化。

### 6.1 积分奖励

RewardID=2, 结构为 6 主题 x 11 段位 x 3 档, 共 198 行。玩家本轮积分达到 PointsDemand 阈值即可领取, 领取给目标积分道具 Point 和 giftid 奖励。轮次结束未领的由系统邮件补发。

### 6.2 目标奖励

RewardID=1, 3 档, 全段位通用 CompetitionRank=2001。玩家本阶段累计目标积分道具达到 2/8/18 即可领取 giftid 1417000/1417001/1417002。

### 6.3 排行奖励

RewardID=3, 5 档排名区间: [1], [2], [3], [4,5], [6,20]。每日阶段积分总量在匹配池内排名, 每阶段 UTC 0 点结算并邮件发放。至少获得 1 积分才有排名奖励; 0 积分无排名奖励。

## 七、邮件与结算

积分宝箱和目标宝箱未手动领取时, 活动刷新通过 CActvOnline.MailUseActvID 邮件补发。排行榜奖励每日结算使用邮件 id 18000017。结算顺序: 积分奖励, 目标奖励, 排名奖励。

## 八、动态层

### 8.1 UI 导航与流转

常规活动主界面点击军备竞赛页签进入主界面。主界面支持货币区图标跳通用货币获取弹窗、规则 tips、日历按钮打开竞赛主题说明、目标奖励宝箱领取或查看、积分奖励宝箱领取、任务跳转、查看更多任务扩展弹窗、排行榜头像查看玩家主页、排名奖励宝箱 tips、返回上级界面。

### 8.2 状态机

活动整体: 未开启 -> 服务器达开服天数 + 玩家灯塔 7 级 -> 次日 UTC 0 点匹配 -> 7 阶段 x 6 轮循环 -> 第 7 天 UTC 24 点结束。每日 UTC 0 点结算前一日并开新一轮匹配。轮次刷新会切换下一轮主题并重置本轮积分奖励宝箱, 目标积分道具不重置。

### 8.3 异常与边界

排行榜第一名积分为 0 时进度条显示 0%。积分相同时先达到者排前。多人积分均为 0 时随机排序且无排名奖励。玩家积分为 0 时无排行奖励且不显示奖励宝箱图标。玩家未加入联盟时隐藏联盟代号。未自定义头像显示默认头像。第三阶段奖励完成后目标进度条 b 锁定第三阶段值。倒计时不足 1 小时或分钟时补 00。无可匹配玩家时池内仅玩家本人。

## 九、实现 vs 构想差异

实际配置与策划案构想差异: 匹配段位使用独立 CArmsRaceRank 表; 主题数从 5 类变为 6 类; 任务数远多于示例且包含通用 701; Reward 增加 Class 字段并使用 giftid; CompetitionRank 同字段两义; Kind 增加 Banner 和 Recommend; Task 增加 Icon 和 Group; 跨服分组表不在本配置文件, 归属 CCrossServerGroup。

## 十、待补清单

无。

## 十一、关联

实现层配置: H活动_军备竞赛配置。活动调度: H活动配置 CActvOnline。任务类型路由: R任务配置 与 任务功能。奖励反查: J奖励配置 与 Gift礼包配置。解锁中枢: CUnlockConfig。本地化: ArmRace_* 文本 key。

---

# 字典/H活动_军备竞赛配置

# H活动_军备竞赛配置 · 字段字典 · V1.0

> 完整字段字典, 5 sheet。设计意图见 军备竞赛。字段可见性: ￥ / ￥=s 服务端, ￥=c 客户端, # 注释列。5 sheet 字段均为服务端。表头约定: row1 中文名, row2 英文 id, row3 可见性, row4 类型, row5-7 注释, r8 起为数据。

## 一、5 sheet 总览

| Sheet | 行列 | 用途 |
|---|---|---|
| CArmRaceStage | 49x6, 42 数据行 | 赛程编排: 7 阶段 x 6 轮, 每轮 4h 指定主题 |
| CArmsRaceKind | 13x6, 6 数据行 | 6 大竞赛主题, 各含任务 / 推荐 / banner |
| CArmsRaceTask | 60x8, 53 数据行 | 任务定义: 完成条件 + 积分 + 图标 + 折叠组 |
| CArmsRaceReward | 213x9, 206 数据行 | 三类奖励: 目标 3 + 积分 198 + 排行 5 |
| CArmsRaceRank | 19x3, 12 数据行 | 匹配段位: 阶段段位 11 档 + 轮次段位 1 档 |

全表 ContentID = 6001。

## 二、跨表关系

CArmRaceStage 通过 ArmsRaceKindID 指向 CArmsRaceKind。CArmsRaceKind 通过 IncludeTask 指向 CArmsRaceTask。CArmsRaceTask 通过 ClassID 指向 R任务配置任务类型枚举, Params 可能指向建筑 / 科研 / 士兵 / 货船 / 道具 id。CArmsRaceReward 中 RewardID=1 为目标奖励, CompetitionRank 指向 CArmsRaceRank id 2001; RewardID=2 为积分奖励, Class 指向主题, CompetitionRank 指向 CArmsRaceRank id 1001-1011; RewardID=3 为排行奖励, CompetitionRank 是排名区间而不是段位 id。Reward 字段指向 J奖励配置 giftid。

## 三、CArmRaceStage 字段

字段: ID, ContentID, StageID, RoundID, Time, ArmsRaceKindID。StageID 为 1-7, RoundID 为 1-6, Time 为 UTC 开始点 0/4/8/12/16/20, ArmsRaceKindID 指向主题 id 1-6。

完整主题编排: 阶段1 = 6/3/1/6/5/4; 阶段2 = 2/1/5/3/1/6; 阶段3 = 4/5/2/1/3/2; 阶段4 = 4/6/3/4/2/5; 阶段5 = 6/3/2/4/3/1; 阶段6 = 3/4/2/6/1/5; 阶段7 = 1/6/4/2/3/5。

## 四、CArmsRaceKind 字段

字段: ID, ContentID, ClassDes, IncludeTask, Recommend, Banner。主题 id 1-6 分别为英雄养成、城市建设、士兵提升、科技研发、船只养成、无人机/神器。Banner 路径模式为 Assets/NewGameDemo/Res/UI/Textures/ArmsRace/ui_activity_{hero/building/soldier/tech/ship/artifact}.png。

## 五、CArmsRaceTask 字段

字段: ID, ClassID, Count, Params, QuestDes, Point, Icon, Group。任务样本: 101 招募 1 次英雄 400 分; 102 单次最低消耗 2000 英雄经验 10 分; 201 提升 1 点建筑战力 10 分; 202 使用 1 分钟建筑加速 100 分; 301 使用 1 分钟训练加速 100 分; 302-311 训练 1 个 1-10 级士兵每级 +10 分; 401 提升 1 点科研战力 10 分; 402 使用 1 分钟科研加速 100 分; 502 消耗珍贵木材 10 分; 503 消耗船只蓝图 100 分; 511-540 发送 1 次 1-30 级货船每级 +100 分; 601 消耗海魂石; 602 消耗行动力; 701 购买包含宝石的礼包。

ClassID 速查: 206 招募英雄, 217 英雄经验, 890 提升战力, 892 加速, 410 训练士兵, 3001 发货船, 3011 发分级货船, 891 消耗道具, 895 购买礼包, 701 行动力。

## 六、CArmsRaceReward 字段

字段: ID, RewardID, Class, CompetitionRank, Stage, Point, PointsDemand, Reward, Value。RewardID=1 目标奖励 3 行: 1000 Stage1 PointsDemand2 Reward1417000; 1001 Stage2 PointsDemand8 Reward1417001; 1002 Stage3 PointsDemand18 Reward1417002。RewardID=2 积分奖励 198 行: 6 主题 x 11 段位 x 3 档。RewardID=3 排行奖励 5 行: 3000 [1], 3001 [2], 3002 [3], 3003 [4,5], 3004 [6,20]。

## 七、CArmsRaceRank 字段

字段: ID, Type, Rank。Type1 积分奖励段位 id 1001-1011: [7,9], [10,12], [13,14], [15,16], [17,18], [19,20], [21,22], [23,24], [25,26], [27,28], [29,30]。Type2 目标奖励段位 id 2001: [7,30]。

## 八、关联

设计层: 军备竞赛。活动调度: H活动配置 CActvOnline ContentID 6001。任务类型: R任务配置。奖励反查: J奖励配置 和 Gift礼包配置。解锁: CUnlockConfig。本地化: ArmRace_* 文本 key。

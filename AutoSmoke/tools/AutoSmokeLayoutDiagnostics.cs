using UnityEngine;
using UnityEditor;
using System.Reflection;
using System.Collections.Generic;
using System.IO;

namespace AutoSmoke.Editor
{
    /// <summary>
    /// AutoSmoke Unity Editor 布局诊断工具（改进版）
    /// 读取 GameView 中游戏渲染区域的准确坐标
    /// </summary>
    public class AutoSmokeLayoutDiagnostics
    {
        private static string OutputPath
        {
            get
            {
                string repoRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
                string configDir = Path.Combine(repoRoot, "AutoSmoke", "config");
                Directory.CreateDirectory(configDir);
                return Path.Combine(configDir, "unity_layout_diagnostics.txt");
            }
        }

        [MenuItem("AutoSmoke/诊断/打印布局信息")]
        private static void PrintLayoutInfo()
        {
            Debug.Log("AutoSmoke: 开始读取 Unity 布局信息...");
            
            var lines = new List<string>
            {
                "============================================================",
                "AutoSmoke Unity Editor 布局诊断（改进版）",
                "时间: " + System.DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                "============================================================",
                ""
            };

            try
            {
                // 1. 查找 GameView
                lines.Add("【1】查找 GameView:");
                lines.Add("");
                
                var gameViews = Resources.FindObjectsOfTypeAll<EditorWindow>();
                EditorWindow gameView = null;
                
                foreach (var window in gameViews)
                {
                    if (window == null) continue;
                    if (window.GetType().FullName.Contains("GameView"))
                    {
                        gameView = window;
                        break;
                    }
                }

                if (gameView == null)
                {
                    lines.Add("  ❌ 未找到 GameView!");
                    File.WriteAllLines(OutputPath, lines);
                    Debug.LogError("AutoSmoke: 未找到 GameView!");
                    EditorUtility.DisplayDialog("AutoSmoke 错误", "未找到 GameView!", "OK");
                    return;
                }

                lines.Add($"  ✅ 找到 GameView!");
                lines.Add($"     标题: {gameView.titleContent.text}");
                lines.Add($"     类型: {gameView.GetType().FullName}");
                lines.Add("");

                // 2. 读取 GameView 的 position（整个面板）
                lines.Add("【2】GameView.position（整个面板）:");
                lines.Add("");
                var pos = gameView.position;
                lines.Add($"     x={pos.x}, y={pos.y}");
                lines.Add($"     w={pos.width}, h={pos.height}");
                lines.Add("");

                // 3. 尝试读取 GameView 的内部游戏渲染区域
                lines.Add("【3】GameView 内部游戏渲染区域:");
                lines.Add("");

                var gameViewType = gameView.GetType();

                // 方法1: 读取 m_GameViewRect 或类似字段
                var rectFields = new string[]
                {
                    "m_GameViewRect",
                    "m_ClientRect",
                    "gameViewRect",
                    "clientRect",
                    "_gameViewRect",
                    "_clientRect"
                };

                foreach (var fieldName in rectFields)
                {
                    var field = gameViewType.GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);
                    if (field != null)
                    {
                        var rect = (Rect)field.GetValue(gameView);
                        lines.Add($"  ✅ 找到字段: {fieldName}");
                        lines.Add($"     x={rect.x}, y={rect.y}");
                        lines.Add($"     w={rect.width}, h={rect.height}");
                        lines.Add("");
                    }
                }

                // 方法2: 读取 GetGameViewRect() 方法
                var rectMethods = new string[]
                {
                    "GetGameViewRect",
                    "GetClientRect",
                    "gameViewRect",
                    "GameViewRect"
                };

                foreach (var methodName in rectMethods)
                {
                    var method = gameViewType.GetMethod(methodName, BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
                    if (method != null)
                    {
                        var rect = (Rect)method.Invoke(gameView, null);
                        lines.Add($"  ✅ 找到方法: {methodName}()");
                        lines.Add($"     x={rect.x}, y={rect.y}");
                        lines.Add($"     w={rect.width}, h={rect.height}");
                        lines.Add("");
                    }
                }

                // 方法3: 使用反射调用 GameView 的 GetMainPlayModeViewSize
                var getSizeMethod = gameViewType.GetMethod("GetMainPlayModeViewSize", BindingFlags.NonPublic | BindingFlags.Static);
                if (getSizeMethod != null)
                {
                    var size = (Vector2)getSizeMethod.Invoke(null, null);
                    lines.Add($"  ✅ 找到方法: GetMainPlayModeViewSize()");
                    lines.Add($"     size={size.x} x {size.y}");
                    lines.Add("");
                }

                // 方法4: 读取当前选中的游戏分辨率
                lines.Add("【4】当前游戏分辨率设置:");
                lines.Add("");

                var selectedSizeField = gameViewType.GetField("m_SelectedSize", BindingFlags.NonPublic | BindingFlags.Instance);
                if (selectedSizeField != null)
                {
                    var selectedSize = selectedSizeField.GetValue(gameView);
                    lines.Add($"  ✅ 找到字段: m_SelectedSize");
                    lines.Add($"     value={selectedSize}");
                    lines.Add("");
                }

                // 方法5: 强制刷新 GameView 并读取位置
                lines.Add("【5】强制刷新 GameView:");
                lines.Add("");

                // 调用 Repaint
                gameView.Repaint();
                lines.Add($"  ✅ 已调用 Repaint()");

                // 等待一帧
                EditorApplication.delayCall += () =>
                {
                    // 再次读取 position
                    var newPos = gameView.position;
                    lines.Add($"  ✅ 刷新后 position: x={newPos.x}, y={newPos.y}, w={newPos.width}, h={newPos.height}");
                    
                    // 保存文件
                    File.WriteAllLines(OutputPath, lines);
                    Debug.Log($"AutoSmoke: 布局信息已保存到: {OutputPath}");
                    EditorUtility.DisplayDialog("AutoSmoke", $"布局信息已保存到:\n{OutputPath}", "OK");
                };

                lines.Add("");
                lines.Add("============================================================");
                lines.Add("注意: 部分信息可能在 delayCall 中更新");
                lines.Add("============================================================");

                // 先保存一次（delayCall 中的保存可能失败）
                File.WriteAllLines(OutputPath, lines);
                Debug.Log($"AutoSmoke: 布局信息已保存到: {OutputPath}");
                EditorUtility.DisplayDialog("AutoSmoke", $"布局信息已保存到:\n{OutputPath}\n\n（注意：部分信息可能在延迟回调中更新）", "OK");
            }
            catch (System.Exception e)
            {
                lines.Add("");
                lines.Add("【错误】");
                lines.Add(e.ToString());
                
                File.WriteAllLines(OutputPath, lines);
                Debug.LogError($"AutoSmoke 错误: {e.Message}");
                EditorUtility.DisplayDialog("AutoSmoke 错误", e.Message, "OK");
            }
        }
    }
}

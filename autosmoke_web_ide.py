"""Web IDE service for AutoSmoke.

Only depends on project-relative paths for cross-machine compatibility.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from AutoSmoke.config_manager import get_game_resolution, set_game_resolution

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
AUTOSMOKE_DIR = PROJECT_ROOT / "AutoSmoke"
CONFIG_FILE = AUTOSMOKE_DIR / "config.json"


def resolve_script_path(script_name: str) -> Path:
    direct = AUTOSMOKE_DIR / script_name
    if direct.exists():
        return direct

    matches = list(AUTOSMOKE_DIR.glob(f"**/{script_name}"))
    if matches:
        return matches[0]

    return direct


@app.route("/")
def index():
    config = load_config()
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AutoSmoke Web IDE</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
            .section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }
            .form-group { margin: 15px 0; }
            label { display: inline-block; width: 150px; font-weight: bold; }
            input[type="number"] { padding: 8px; width: 120px; }
            button { background: #4CAF50; color: #fff; padding: 10px 16px; border: 0; border-radius: 4px; margin: 5px; }
            button:hover { background: #45a049; }
            button:disabled { background: #ccc; }
            .btn-blue { background: #2196F3; }
            .btn-red { background: #f44336; }
            #output {
                background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px;
                height: 360px; overflow-y: auto; white-space: pre-wrap; font-family: Consolas, monospace;
            }
            .success { color: #4CAF50; }
            .error { color: #f44336; }
            .info { color: #2196F3; }
        </style>
    </head>
    <body>
      <h1>AutoSmoke IDE - Unity</h1>
      <div class="section">
        <h2>Game resolution</h2>
        <div class="form-group">
          <label>Width</label>
          <input id="width" type="number" value="{{ width }}" min="100" max="10000"> px
        </div>
        <div class="form-group">
          <label>Height</label>
          <input id="height" type="number" value="{{ height }}" min="100" max="10000"> px
        </div>
        <button onclick="saveConfig()">Save config</button>
      </div>

      <div class="section">
        <h2>Run scripts</h2>
        <button class="btn-blue" onclick="runScript('visualize_clickable_elements.py')">Visualize clickable elements</button>
        <button class="btn-blue" onclick="runScript('locate_active_region.py')">Locate active region</button>
        <br><br>
        <button disabled>Auto click test</button>
        <button disabled>Generate test cases</button>
      </div>

      <div class="section">
        <h2>Run output</h2>
        <div id="output"></div>
        <br>
        <button class="btn-red" onclick="clearOutput()">Clear</button>
      </div>

      <script>
        function append(text, cls) {
          const output = document.getElementById('output');
          output.innerHTML += `<span class="${cls}">${text}</span>\n`;
          output.scrollTop = output.scrollHeight;
        }

        function saveConfig() {
          const width = document.getElementById('width').value;
          const height = document.getElementById('height').value;
          fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ width: parseInt(width), height: parseInt(height) })
          }).then(r => r.json()).then(data => {
            if (data.success) {
              append('Config saved', 'success');
            } else {
              append('Save failed: ' + data.error, 'error');
            }
          });
        }

        function runScript(scriptName) {
          append('Start: ' + scriptName, 'info');
          fetch('/api/run/' + scriptName).then(r => r.json()).then(data => {
            if (data.success) {
              append('Done: ' + data.message, 'success');
            } else {
              append('Failed: ' + data.message, 'error');
            }
          }).catch(err => append('Request failed: ' + err, 'error'));
        }

        function clearOutput() {
          document.getElementById('output').textContent = '';
        }
      </script>
    </body>
    </html>
    """

    return render_template_string(
        html,
        width=config["game_resolution"]["width"],
        height=config["game_resolution"]["height"],
    )


@app.route('/api/config', methods=['POST'])
def api_save_config():
    try:
        data = request.get_json(force=True)
        width = int(data['width'])
        height = int(data['height'])
        config = load_config()
        config['game_resolution'] = {'width': width, 'height': height}
        save_config(config)
        return jsonify({'success': True})
    except Exception as exc:  # pragma: no cover
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/run/<script_name>')
def api_run_script(script_name: str):
    script_path = resolve_script_path(script_name)
    if not script_path.exists():
        return jsonify({'success': False, 'message': f'Script not found: {script_name}'})

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(AUTOSMOKE_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            return jsonify({'success': True, 'message': result.stdout or 'Script finished successfully'})
        return jsonify({'success': False, 'message': result.stderr or result.stdout or 'Script failed'})
    except Exception as exc:  # pragma: no cover
        return jsonify({'success': False, 'message': str(exc)})


def load_config():
    if not CONFIG_FILE.exists():
        return create_default_config()

    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as exc:
        print(f"Load config failed: {exc}")
        return create_default_config()


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open('w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def create_default_config():
    default = {
        'game_resolution': {
            'width': 1170,
            'height': 2532,
        },
        'auto_detect_region': True,
        'black_threshold': 30,
    }
    save_config(default)
    return default


@app.route('/api/diag')
def api_diag():
    return jsonify({'autosmoke_dir': str(AUTOSMOKE_DIR)})


if __name__ == '__main__':
    print('=' * 80)
    print('AutoSmoke Web IDE')
    print('=' * 80)
    print('Visit: http://localhost:5000')
    print('Press Ctrl+C to exit.')
    print('=' * 80)

    app.run(host='0.0.0.0', port=5000, debug=False)

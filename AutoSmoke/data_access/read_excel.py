import pandas as pd
import sys
import os
from pathlib import Path

file = str((Path(__file__).resolve().parents[1] / "参考资料" / "用例模板.xlsx"))
print(f"尝试读取文件: {file}")
print(f"文件是否存在: {os.path.exists(file)}")

try:
    xl = pd.ExcelFile(file)
    print(f'\n工作表列表: {xl.sheet_names}')
    
    for sheet in xl.sheet_names:
        df = pd.read_excel(file, sheet_name=sheet)
        print(f'\n====== 工作表: {sheet} ======')
        print(f'行数: {len(df)}, 列数: {len(df.columns)}')
        print(f'列名: {list(df.columns)}')
        print('\n所有数据:')
        print(df.to_string())
        
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()

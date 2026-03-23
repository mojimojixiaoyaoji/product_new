import pandas as pd
import os

# 定义文件路径
file1 = '生产主数据.xlsx'
file2 = '工艺主数据清洗后.xlsx'

# 检查文件是否存在
if not os.path.exists(file1):
    print(f"文件 {file1} 不存在")
    exit(1)
if not os.path.exists(file2):
    print(f"文件 {file2} 不存在")
    exit(1)

print(f"对比文件: {file1} vs {file2}\n")

# 读取Excel文件中的所有工作表
def read_all_sheets(file_path):
    xls = pd.ExcelFile(file_path)
    sheets = {}
    for sheet_name in xls.sheet_names:
        try:
            sheets[sheet_name] = xls.parse(sheet_name)
            print(f"{file_path} 包含工作表: {sheet_name} (行数: {len(sheets[sheet_name])}, 列数: {len(sheets[sheet_name].columns)}")
        except Exception as e:
            print(f"读取 {sheet_name} 时出错: {e}")
    return sheets

# 读取两个文件的所有工作表
sheets1 = read_all_sheets(file1)
sheets2 = read_all_sheets(file2)

print("\n" + "="*60)
print("工作表对比:")
print("="*60)

# 比较工作表数量
print(f"\n工作表数量:")
print(f"{file1}: {len(sheets1)} 个工作表")
print(f"{file2}: {len(sheets2)} 个工作表")

# 找出共同和独有的工作表
common_sheets = set(sheets1.keys()) & set(sheets2.keys())
unique_sheets1 = set(sheets1.keys()) - set(sheets2.keys())
unique_sheets2 = set(sheets2.keys()) - set(sheets1.keys())

print(f"\n共同工作表: {list(common_sheets)}")
print(f"{file1} 独有工作表: {list(unique_sheets1)}")
print(f"{file2} 独有工作表: {list(unique_sheets2)}")

# 比较共同工作表的内容
print("\n" + "="*60)
print("共同工作表内容对比:")
print("="*60)

for sheet_name in common_sheets:
    print(f"\n工作表: {sheet_name}")
    df1 = sheets1[sheet_name]
    df2 = sheets2[sheet_name]
    
    # 比较列名
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    common_cols = cols1 & cols2
    unique_cols1 = cols1 - cols2
    unique_cols2 = cols2 - cols1
    
    print(f"  列数:")
    print(f"    {file1}: {len(cols1)} 列")
    print(f"    {file2}: {len(cols2)} 列")
    
    if unique_cols1:
        print(f"  {file1} 独有列: {list(unique_cols1)}")
    if unique_cols2:
        print(f"  {file2} 独有列: {list(unique_cols2)}")
    
    # 比较行数
    print(f"  行数:")
    print(f"    {file1}: {len(df1)} 行")
    print(f"    {file2}: {len(df2)} 行")
    
    # 如果有共同列，尝试比较数据
    if common_cols:
        print(f"  共同列: {list(common_cols)}")
        # 简单比较数据行数差异
        if len(df1) != len(df2):
            print(f"  警告: 行数不同")
        else:
            # 尝试比较数据内容
            try:
                # 只比较共同列
                df1_common = df1[list(common_cols)]
                df2_common = df2[list(common_cols)]
                
                # 重置索引后比较
                df1_common = df1_common.reset_index(drop=True)
                df2_common = df2_common.reset_index(drop=True)
                
                # 找出不同的行
                diff_rows = []
                for i in range(min(len(df1_common), len(df2_common))):
                    if not df1_common.iloc[i].equals(df2_common.iloc[i]):
                        diff_rows.append(i)
                
                if diff_rows:
                    print(f"  发现 {len(diff_rows)} 行数据不同")
                    # 显示前5个不同的行
                    for i, row_idx in enumerate(diff_rows[:5]):
                        print(f"    第 {row_idx+1} 行差异:")
                        for col in common_cols:
                            val1 = df1_common.iloc[row_idx][col]
                            val2 = df2_common.iloc[row_idx][col]
                            if val1 != val2:
                                print(f"      {col}: {val1} vs {val2}")
                    if len(diff_rows) > 5:
                        print(f"    ... 还有 {len(diff_rows)-5} 行差异未显示")
                else:
                    print(f"  数据内容完全相同")
            except Exception as e:
                print(f"  比较数据时出错: {e}")

print("\n" + "="*60)
print("对比完成")
print("="*60)

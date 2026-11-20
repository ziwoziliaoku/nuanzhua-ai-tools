# 12-asset-organizer.py
# 暖爪咖啡 · 素材整理助手（第 1 步：只扫描，不动文件）
#
# 这个版本只做三件事：
#   1. 数一数指定文件夹里有多少文件
#   2. 按内容猜它们是干嘛的（海报 / 包装 / 吉祥物 / 视频 / 文档……）
#   3. 找出疑似重复的文件（比如 xxx (1).pdf、xxx (2).pdf）
#
# 它绝对不会移动、删除或修改任何文件。只是"体检报告"。
#
# 用法（在 代码练习 目录下）：
#   python 12-asset-organizer.py --folder "C:\Users\wjy\Downloads"

import argparse
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

# ========== 分类规则表 ==========
# 左边是"文件名里出现什么词"，右边是"归到哪一类"
NAME_RULES = [
    ("jimeng", "AI出图（即梦）"),
    ("海报", "海报"),
    ("poster", "海报"),
    ("包装", "包装物料"),
    ("包装展示", "包装物料"),
    ("吉祥物", "IP角色"),
    ("江天", "IP角色"),
    ("小熊猫", "IP角色"),
    ("杯", "包装物料"),
    ("袋", "包装物料"),
]

# 扩展名对应的兜底分类
EXT_RULES = {
    ".png": "图片（未分类）",
    ".jpg": "图片（未分类）",
    ".jpeg": "图片（未分类）",
    ".jfif": "图片（未分类）",
    ".mp4": "视频",
    ".mov": "视频",
    ".pdf": "文档",
    ".doc": "文档",
    ".docx": "文档",
    ".xls": "表格",
    ".xlsx": "表格",
    ".csv": "表格",
    ".py": "代码",
    ".exe": "安装包",
    ".zip": "压缩包",
    ".txt": "文本",
}


def guess_category(file_path: Path) -> str:
    """先按文件名里的关键词猜，猜不到再按扩展名兜底。"""
    name_lower = file_path.name.lower()

    for keyword, category in NAME_RULES:
        if keyword.lower() in name_lower:
            return category

    return EXT_RULES.get(file_path.suffix.lower(), "其他")


def find_duplicate_groups(files: list) -> dict:
    """找出 Windows 那种「xxx (1).pdf、xxx (2).pdf」的重复下载。

    思路：把「 (数字)」这部分去掉，看剩下的名字有没有撞车。
    """
    groups = {}
    for file_path in files:
        stem = file_path.stem                      # 去掉扩展名的文件名
        base = stem
        # 如果结尾像「 (1)」「 (12)」，就把它砍掉
        if base.endswith(")") and " (" in base:
            head, _, tail = base.rpartition(" (")
            if tail[:-1].isdigit():
                base = head

        key = base + file_path.suffix.lower()
        groups.setdefault(key, []).append(file_path.name)

    # 只保留真正的"一组里有 2 个以上"的
    return {k: v for k, v in groups.items() if len(v) > 1}


def size_band(size_bytes: int) -> str:
    """把字节数翻译成人能看懂的大小段。"""
    mb = size_bytes / (1024 * 1024)
    if mb < 1:
        return "小于 1MB"
    if mb < 5:
        return "1-5MB"
    if mb < 20:
        return "5-20MB"
    return "20MB 以上"


def main():
    parser = argparse.ArgumentParser(description="素材整理助手：扫描文件夹，出一份体检报告")
    parser.add_argument("--folder", required=True, help="要扫描的文件夹路径")
    parser.add_argument("--output", default="素材扫描报告.csv", help="报告文件名")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"找不到这个文件夹：{folder}")
        return

    print("=" * 56)
    print("  素材体检报告")
    print("=" * 56)
    print(f"扫描目标：{folder}")
    print()

    # ---------- 1. 收集文件 ----------
    try:
        files = [p for p in folder.iterdir() if p.is_file()]
    except PermissionError:
        print(f"没有权限读取这个文件夹：{folder}")
        return

    total = len(files)
    print(f"一共 {total} 个文件")
    print()

    # ---------- 2. 按分类统计 ----------
    categories = Counter(guess_category(p) for p in files)
    print("按用途分类：")
    for name, count in categories.most_common():
        bar = "█" * min(count, 40)
        print(f"  {name:<12} {count:>4} 个  {bar}")
    print()

    # ---------- 3. 按扩展名统计 ----------
    extensions = Counter(p.suffix.lower() or "(无扩展名)" for p in files)
    print("按格式：")
    for ext, count in extensions.most_common():
        print(f"  {ext:<10} {count:>4} 个")
    print()

    # ---------- 4. 疑似重复 ----------
    dup_groups = find_duplicate_groups(files)
    dup_file_count = sum(len(v) for v in dup_groups.values())
    print(f"疑似重复：{len(dup_groups)} 组，共 {dup_file_count} 个文件")
    for base, names in list(dup_groups.items())[:10]:
        print(f"  [{len(names)} 份] {base}")
    if len(dup_groups) > 10:
        print(f"  ……还有 {len(dup_groups) - 10} 组，见报告文件")
    print()

    # ---------- 5. 体积分布 ----------
    bands = Counter(size_band(p.stat().st_size) for p in files)
    print("体积分布：")
    for band, count in bands.most_common():
        print(f"  {band:<10} {count:>4} 个")
    print()

    # ---------- 6. 写 CSV 报告 ----------
    report_path = Path(args.output)
    with report_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["文件名", "猜测分类", "扩展名", "大小(KB)", "修改时间", "疑似重复组"])
        for p in sorted(files, key=lambda x: x.name):
            try:
                size_kb = round(p.stat().st_size / 1024, 1)
                mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                size_kb, mtime = 0, "读取失败"

            dup_key = ""
            for base, names in dup_groups.items():
                if p.name in names:
                    dup_key = base
                    break

            writer.writerow([p.name, guess_category(p), p.suffix.lower(), size_kb, mtime, dup_key])

    print("=" * 56)
    print(f"详细清单已写入：{report_path.resolve()}")
    print("（这个工具没有移动、删除或修改任何文件）")
    print("=" * 56)


if __name__ == "__main__":
    main()

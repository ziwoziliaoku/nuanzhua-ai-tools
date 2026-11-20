# 12-asset-organizer.py
# 暖爪咖啡 · 素材整理助手
#
# 三种模式：
#   scan  体检——只统计，不出计划（第 1 步）
#   plan  出搬迁计划——算出每个文件该去哪，写成清单，不动文件
#   apply 执行搬迁——按计划真的移动文件，并写日志
#
# 安全设计：
#   1. plan 模式绝不移动任何文件
#   2. apply 模式必须手动输入 YES 才执行
#   3. 每次搬迁都写「搬迁日志.csv」，记录原路径，随时能查、能搬回去
#   4. 目标位置已有同名文件时，自动改名为 xxx_2.png，不覆盖
#
# 用法（在 代码练习 目录下）：
#   python 12-asset-organizer.py --folder "C:\Users\wjy\Downloads" --mode plan
#   python 12-asset-organizer.py --folder "C:\Users\wjy\Downloads" --mode apply

import argparse
import csv
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

# ========== 分类规则 ==========

# 先按文件名里的关键词猜（越靠前优先级越高）
NAME_RULES = [
    ("海报", "海报"),
    ("poster", "海报"),
    ("包装展示", "包装物料"),
    ("包装", "包装物料"),
    ("杯套", "包装物料"),
    ("纸杯", "包装物料"),
    ("纸袋", "包装物料"),
    ("吉祥物", "IP角色"),
    ("江天", "IP角色"),
    ("小熊猫", "IP角色"),
    ("jimeng", "AI出图（即梦）"),
    ("gemini", "AI出图（Gemini）"),
]

# 扩展名兜底
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
    ".ps1": "代码",
    ".exe": "安装包",
    ".msi": "安装包",
    ".zip": "压缩包",
    ".rar": "压缩包",
    ".txt": "文本",
    ".ini": "文本",
}

# 分类 → 目标子文件夹
CATEGORY_FOLDERS = {
    "海报": "01-海报",
    "包装物料": "02-包装物料",
    "IP角色": "03-IP角色",
    "AI出图（即梦）": "04-AI出图",
    "AI出图（Gemini）": "04-AI出图",
    "图片（未分类）": "05-图片-按月",
    "文档": "06-文档",
    "表格": "07-表格",
    "视频": "08-视频",
    "安装包": "09-安装包",
    "代码": "10-代码",
    "文本": "11-文本",
    "压缩包": "12-压缩包",
    "其他": "99-其他",
}

# 疑似重复的文件，先单独放一边，等你自己决定删哪些
DUPLICATE_FOLDER = "00-待清理-重复"


# ========== 基础函数 ==========

def guess_category(file_path: Path) -> str:
    """先按扩展名判断大类，只有图片和视频才靠文件名猜内容。

    为什么这么改：原来的写法让「08-poster-prompt-batch.py」因为文件名带
    poster 被当成海报。代码、文档、表格这些不该看文件名关键词。
    """
    ext = file_path.suffix.lower()

    # 图片和视频：才允许用文件名猜内容（海报 / 包装 / IP 角色 / AI 出图）
    if ext in {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".mp4", ".mov"}:
        name_lower = file_path.name.lower()
        for keyword, category in NAME_RULES:
            if keyword in name_lower:
                return category
        return EXT_RULES.get(ext, "其他")

    # 其他类型：只看扩展名，不看文件名里有没有"海报""包装"这类词
    return EXT_RULES.get(ext, "其他")


def find_duplicate_groups(files: list) -> dict:
    """找出「xxx (1).pdf、xxx (2).pdf」这类重复下载。"""
    groups = {}
    for file_path in files:
        stem = file_path.stem
        base = stem
        if base.endswith(")") and " (" in base:
            head, _, tail = base.rpartition(" (")
            if tail[:-1].isdigit():
                base = head

        key = base + file_path.suffix.lower()
        groups.setdefault(key, []).append(file_path.name)

    return {k: v for k, v in groups.items() if len(v) > 1}


def size_band(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb < 1:
        return "小于 1MB"
    if mb < 5:
        return "1-5MB"
    if mb < 20:
        return "5-20MB"
    return "20MB 以上"


# ========== 模式 1：体检 ==========

def run_scan(folder: Path, output: str) -> None:
    print("=" * 56)
    print("  素材体检报告")
    print("=" * 56)
    print(f"扫描目标：{folder}")
    print()

    try:
        files = [p for p in folder.iterdir() if p.is_file()]
    except PermissionError:
        print(f"没有权限读取这个文件夹：{folder}")
        return

    print(f"一共 {len(files)} 个文件")
    print()

    categories = Counter(guess_category(p) for p in files)
    print("按用途分类：")
    for name, count in categories.most_common():
        bar = "█" * min(count, 40)
        print(f"  {name:<14} {count:>4} 个  {bar}")
    print()

    extensions = Counter(p.suffix.lower() or "(无扩展名)" for p in files)
    print("按格式：")
    for ext, count in extensions.most_common():
        print(f"  {ext:<10} {count:>4} 个")
    print()

    dup_groups = find_duplicate_groups(files)
    dup_file_count = sum(len(v) for v in dup_groups.values())
    print(f"疑似重复：{len(dup_groups)} 组，共 {dup_file_count} 个文件")
    for base, names in list(dup_groups.items())[:10]:
        print(f"  [{len(names)} 份] {base}")
    if len(dup_groups) > 10:
        print(f"  ……还有 {len(dup_groups) - 10} 组，见报告文件")
    print()

    bands = Counter(size_band(p.stat().st_size) for p in files)
    print("体积分布：")
    for band, count in bands.most_common():
        print(f"  {band:<10} {count:>4} 个")
    print()

    report_path = Path(output)
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
    print("（这个模式没有移动、删除或修改任何文件）")
    print("=" * 56)


# ========== 模式 2/3：出计划 & 执行 ==========

def build_plan(folder: Path) -> list:
    """算出每个文件该搬去哪，返回计划列表。"""
    files = [p for p in folder.iterdir() if p.is_file()]
    dup_groups = find_duplicate_groups(files)

    # 先把"属于重复组"的文件名挑出来
    dup_names = set()
    for names in dup_groups.values():
        dup_names.update(names)

    plan = []
    for p in sorted(files, key=lambda x: x.name):
        category = guess_category(p)
        sub_folder = CATEGORY_FOLDERS.get(category, "99-其他")

        # 未分类的图片，按修改月份再分一层
        if category == "图片（未分类）":
            try:
                month = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m")
            except OSError:
                month = "未知月份"
            sub_folder = f"05-图片-按月/{month}"

        # 疑似重复的，单独放
        if p.name in dup_names:
            sub_folder = DUPLICATE_FOLDER

        plan.append(
            {
                "原路径": p,
                "分类": category,
                "目标文件夹": sub_folder,
                "目标文件名": p.name,
            }
        )

    return plan


def print_plan(plan: list) -> None:
    print()
    print("各地要去的地方：")
    counts = Counter(item["目标文件夹"].split("/")[0] for item in plan)
    for folder_name, count in sorted(counts.items()):
        print(f"  {folder_name:<18} {count:>4} 个文件")
    print()

    print("前 15 个具体例子：")
    for item in plan[:15]:
        print(f"  {item['原路径'].name}")
        print(f"      → {item['目标文件夹']}\\")
    if len(plan) > 15:
        print(f"  ……还有 {len(plan) - 15} 个，见计划表")


def write_plan_csv(plan: list, output: str) -> Path:
    path = Path(output)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["原文件名", "猜测分类", "目标文件夹", "目标文件名"])
        for item in plan:
            writer.writerow(
                [item["原路径"].name, item["分类"], item["目标文件夹"], item["目标文件名"]]
            )
    return path


def run_plan(folder: Path) -> list:
    print("=" * 56)
    print("  搬迁计划（没有任何文件被移动）")
    print("=" * 56)

    plan = build_plan(folder)
    print(f"一共 {len(plan)} 个文件")
    print_plan(plan)

    plan_file = write_plan_csv(plan, "搬迁计划.csv")
    print()
    print(f"完整计划表已写入：{plan_file.resolve()}")
    print("=" * 56)
    print("看过了觉得没问题，再用 --mode apply 真正执行。")
    print("=" * 56)
    return plan


def unique_target(target: Path) -> Path:
    """目标位置已有同名文件时，自动改名为 xxx_2.ext、xxx_3.ext……"""
    if not target.exists():
        return target

    stem, suffix = target.stem, target.suffix
    index = 2
    while True:
        candidate = target.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def run_apply(folder: Path) -> None:
    print("=" * 56)
    print("  执行搬迁")
    print("=" * 56)

    plan = build_plan(folder)
    root = folder / "_整理结果"

    print(f"将把 {len(plan)} 个文件移动到：{root}")
    print("原文件夹里的文件会被移走（不是复制），但每一次移动都会记进日志。")
    print()
    answer = input("确认执行请输入大写 YES，其他任意键取消：").strip()
    if answer != "YES":
        print("已取消，什么都没动。")
        return

    log_rows = []
    moved = 0
    skipped = 0

    for item in plan:
        source = item["原路径"]
        target_dir = root / item["目标文件夹"]
        target_dir.mkdir(parents=True, exist_ok=True)
        target = unique_target(target_dir / item["目标文件名"])

        try:
            shutil.move(str(source), str(target))
            moved += 1
            log_rows.append([source.name, str(source), str(target), "已移动"])
            print(f"  ✓ {source.name} → {item['目标文件夹']}")
        except Exception as error:
            skipped += 1
            log_rows.append([source.name, str(source), "", f"跳过：{type(error).__name__}: {error}"])
            print(f"  ✗ {source.name} 跳过（{type(error).__name__}）")

    log_path = Path("搬迁日志.csv")
    with log_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["原文件名", "原完整路径", "新完整路径", "状态"])
        writer.writerows(log_rows)

    print()
    print("=" * 56)
    print(f"移动成功：{moved} 个")
    print(f"跳过：{skipped} 个（多半是文件正在被别的程序占用）")
    print(f"日志：{log_path.resolve()}")
    print("=" * 56)


# ========== 入口 ==========

def main():
    parser = argparse.ArgumentParser(description="素材整理助手")
    parser.add_argument("--folder", required=True, help="要处理的文件夹路径")
    parser.add_argument("--mode", default="scan", choices=["scan", "plan", "apply"], help="scan=体检，plan=出计划，apply=执行")
    parser.add_argument("--output", default="素材扫描报告.csv", help="scan 模式的报告文件名")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"找不到这个文件夹：{folder}")
        return

    if args.mode == "scan":
        run_scan(folder, args.output)
    elif args.mode == "plan":
        run_plan(folder)
    else:
        run_apply(folder)


if __name__ == "__main__":
    main()

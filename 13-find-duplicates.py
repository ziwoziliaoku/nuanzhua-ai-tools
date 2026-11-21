# -*- coding: utf-8 -*-
"""
13-find-duplicates.py   暖爪咖啡 · 真重复文件查找器

为什么要有这个工具：
    12 判重复只看文件名（xxx (1).png），但文件名靠不住：
      - 名字一样，内容可能不一样（重新导出过、后来又编辑过）
      - 名字完全不同，内容也可能一模一样（不同地方下载的同一张图）

所以这里按「内容」判断，分两级：
    第一级 比大小 —— 大小不同，绝不可能是同一份内容，直接排除。
                     这一步几乎不耗时，能筛掉绝大多数文件。
    第二级 算指纹 —— 只有大小相同的，才算 MD5。指纹一样才是真重复。

MD5 是什么：
    把整个文件的内容揉成一个 32 位的字符串。内容改动一个字节，
    这个字符串就完全变样。就像指纹：同一个人永远一样，换人就完全不同。

为什么分块读：
    一个 200MB 的视频一次塞进内存，机器会卡。所以每次只读 1MB，
    读完一段算一段，最后拼成一个指纹。

用法（在 代码练习 目录下）：
    只分析：
        python 13-find-duplicates.py --folder "C:\\Users\\wjy\\Downloads\\_整理结果\\00-待清理-重复"

    分析并真的搬走多余份：
        python 13-find-duplicates.py --folder "..." --move-to "C:\\Users\\wjy\\Downloads\\_重复待清理"

安全设计：
    1. 不带 --move-to，就只读，绝不动任何文件
    2. 带 --move-to 时，必须手动输入 YES 才开始
    3. 每一组永远保留一份，绝不整组清空
    4. 只移动、不删除；移错了可以照着日志搬回来

今天有两个空留给你填，都标了 TODO。
"""

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

CHUNK_SIZE = 1024 * 1024   # 每次读 1MB


def file_hash(path, chunk_size=CHUNK_SIZE):
    """算一个文件的 MD5 指纹，分块读，不把整个文件塞进内存。"""
    md5 = hashlib.md5()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            md5.update(block)
    return md5.hexdigest()


def base_name(path):
    """把「xxx (1).png」还原成「xxx.png」，用来找名字像的那批。"""
    stem = path.stem
    if stem.endswith(")") and " (" in stem:
        head, _, tail = stem.rpartition(" (")
        if tail[:-1].isdigit():
            stem = head
    return stem + path.suffix.lower()


def human_size(num_bytes):
    """把字节数换成人话：430.0 MB 比 450887680 好懂。"""
    mb = num_bytes / (1024 * 1024)
    if mb < 1:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{mb:.1f} MB"


def collect_files(folder):
    """拿到文件夹里的所有普通文件。"""
    return [p for p in folder.iterdir() if p.is_file()]


def find_true_duplicates(files):
    """两级判断，返回（真重复组, 大小相同但内容不同 的组）。

    返回的每一组是这样一本字典：
        {"hash": "abc123...", "size": 12345, "files": [路径1, 路径2, ...]}
    """
    # ---- 第一级：按大小分组 ----
    by_size = {}
    for p in files:
        try:
            size = p.stat().st_size
        except OSError:
            continue          # 读不到就跳过，不因为一个坏文件中断全流程
        by_size.setdefault(size, []).append(p)

    # 只有「大小相同且不止一份」的，才值得花时间去算指纹
    same_size_groups = [g for g in by_size.values() if len(g) > 1]

    # ---- 第二级：组内按指纹分组 ----
    true_groups = []
    false_groups = []

    for group in same_size_groups:
        by_hash = {}
        for p in group:
            fingerprint = file_hash(p)
            by_hash.setdefault(fingerprint, []).append(p)

        different = 0
        for fingerprint, same in by_hash.items():
            if len(same) > 1:
                true_groups.append(
                    {
                        "hash": fingerprint,
                        "size": same[0].stat().st_size,
                        "files": same,
                    }
                )
            else:
                different += 1
        if different > 1:
            false_groups.append(group)

    return true_groups, false_groups


def choose_keeper(files):
    """同一组里，留下哪一份？

    默认的规则：留名字最短的那份。因为下载重复时，系统会给后来的
    加「 (1)」「 (2)」，所以名字越短，越像最早下载的那一份原件。

    TODO 1（你来填）：
        下面这个循环本该找出「名字最短的那份」，但判断那一步还空着。
        请补上两句：如果 p 的名字比 best 短，就把 best 换成 p。

        写完之后应该是这样（缩进要注意，if 里面要再缩一层）：
            for p in files:
                if len(p.name) < len(best.name):
                    best = p

        可以先只想一行：条件是什么？
            答案是：len(p.name) < len(best.name)
    """
    best = files[0]
    for p in files:
        # TODO 1：在这里补 if 判断 + 赋值
        if len(p.name)<len(best.name):
            best=p
        pass
    return best


def print_report(folder, total, true_groups, false_groups, named_groups):
    """把结果打在屏幕上，人看得懂的那种。"""
    print("=" * 60)
    print("  真重复检查报告")
    print("=" * 60)
    print(f"扫描位置：{folder}")
    print(f"一共 {total} 个文件")
    print()

    if not true_groups:
        print("没有发现内容完全相同的文件。")
        return

    extra_count = 0
    wasted = 0
    for item in true_groups:
        extra_count += len(item["files"]) - 1
        wasted += (len(item["files"]) - 1) * item["size"]

    print(f"第一级：按大小筛，有 {len(true_groups)} 组存在内容相同的可能")
    print(f"第二级：算过指纹后，确认 {len(true_groups)} 组是真重复")
    print("-" * 60)

    for index, item in enumerate(true_groups, start=1):
        keeper = choose_keeper(item["files"])
        print(f"[第 {index} 组] 共 {len(item['files'])} 份，每份 {human_size(item['size'])}")
        for p in item["files"]:
            mark = "保留 " if p == keeper else "待清理"
            print(f"    {mark}  {p.name}")
        print()

    print("-" * 60)
    print(f"结论：可以清掉 {extra_count} 份，腾出 {human_size(wasted)}")

    if false_groups:
        print()
        print(f"另外还有 {len(false_groups)} 组「大小一样但内容不同」的，这些不能删：")
        for group in false_groups:
            print("    " + " / ".join(p.name for p in group))

    if named_groups:
        print()
        print(f"名字很像、但体积不同，大概率是两个不同版本，别当重复删：")
        for group in named_groups:
            print(f"    {base_name(group[0])}")
            for p in group:
                print(f"        {p.name}  {human_size(p.stat().st_size)}")
            print()


def write_csv(path, true_groups, named_groups):
    """把结果写成表，Excel 能直接打开。"""
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["组号", "判定", "文件名", "大小(KB)", "MD5指纹", "建议"])

        for index, item in enumerate(true_groups, start=1):
            keeper = choose_keeper(item["files"])
            for p in item["files"]:
                advice = "保留" if p == keeper else "可清理"
                writer.writerow(
                    [index, "真重复", p.name, round(item["size"] / 1024, 1), item["hash"], advice]
                )

        for p_group in named_groups:
            for p in p_group:
                writer.writerow(
                    ["-", "名字像但不同", p.name, round(p.stat().st_size / 1024, 1), "", "保留"]
                )


def run_move(true_groups, move_root):
    """把每组里多余的那几份搬到 move_root，保留的那份原地不动。"""
    move_root = Path(move_root)
    move_root.mkdir(parents=True, exist_ok=True)

    total_extra = sum(len(item["files"]) - 1 for item in true_groups)
    print()
    print("=" * 60)
    print(f"准备把 {total_extra} 个「多余份」搬到：{move_root}")
    print("只是挪位置，不是删除；每组至少留一份。")
    print("=" * 60)

    answer = input("确认搬走请输入大写 YES，直接回车则取消：").strip()
    if answer != "YES":
        print("已取消，什么都没动。")
        return

    log_rows = []
    moved = 0
    for item in true_groups:
        keeper = choose_keeper(item["files"])
        for p in item["files"]:
            if p == keeper:
                continue                       # 保留的那份，原地别动

            target = move_root / p.name
            if target.exists():                # 目标已有同名，加序号，不覆盖
                stem, suffix = target.stem, target.suffix
                index = 2
                while (move_root / f"{stem}_{index}{suffix}").exists():
                    index += 1
                target = move_root / f"{stem}_{index}{suffix}"

            try:
                shutil.move(str(p), str(target))
                moved += 1
                log_rows.append([p.name, str(p), str(target), "已搬走"])
                print(f"  ✓ {p.name}")
            except Exception as error:
                log_rows.append([p.name, str(p), "", f"失败：{type(error).__name__}"])
                print(f"  ✗ {p.name} 失败（{type(error).__name__}）")

    log_path = Path("重复清理日志.csv")
    with log_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["原文件名", "原完整路径", "新完整路径", "状态"])
        writer.writerows(log_rows)

    print()
    print(f"搬走 {moved} 个，日志：{log_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="按内容找真重复文件")
    parser.add_argument("--folder", required=True, help="要检查的文件夹")
    parser.add_argument("--move-to", default=None, help="把多余份搬到这个目录（不填就只分析）")
    parser.add_argument("--output", default="重复清单.csv", help="清单文件名")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        print(f"找不到这个文件夹：{folder}")
        return

    files = collect_files(folder)
    true_groups, false_groups = find_true_duplicates(files)

    # 「名字很像但体积不同」的，单独挑出来，提醒不要误删
    by_base = {}
    for p in files:
        by_base.setdefault(base_name(p), []).append(p)
    named_groups = [
        g
        for g in by_base.values()
        if len(g) > 1 and len({p.stat().st_size for p in g}) > 1
    ]

    print_report(folder, len(files), true_groups, false_groups, named_groups)
    write_csv(args.output, true_groups, named_groups)
    print()
    print(f"清单已写入：{Path(args.output).resolve()}")

    if args.move_to and true_groups:
        run_move(true_groups, args.move_to)
    elif not args.move_to:
        print("（本次只分析，没有动任何文件。要搬走多余份，加 --move-to 参数）")


if __name__ == "__main__":
    main()

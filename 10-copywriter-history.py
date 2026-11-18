# 10-copywriter-history.py
# 暖爪咖啡 · 文案工具 v3（会记账的版本）
#
# 相比 09 只多两件事：
#   1. 每次生成完，往「历史记录.csv」追加一行（时间/产品/季节/风格/文案）
#   2. 可以输入产品名，查这个产品以前写过的所有版本
#
# ===== 今天你要做的事 =====
# 文件里有 3 个 TODO，把每个 TODO 下面的 ____ 换成真正的代码。
# 每个 TODO 上面都写清了要干什么、用什么写。
# 填错没关系，运行时会报错，报错就是提示，我们照着改。
#
# 如果运行报错说「____ 没有定义」，意思就是"这个空你还没填"。

import csv
import os
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ---------- 配置 ----------
API_KEY = os.getenv("ARK_API_KEY")
MODEL_NAME = os.getenv("ARK_MODEL")

if not API_KEY or not MODEL_NAME:
    raise ValueError("环境变量 ARK_API_KEY / ARK_MODEL 没配置好。")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

# 这个就是「目录本」：一个 csv 文件，一行一条记录
HISTORY_FILE = Path("历史记录.csv")
HISTORY_FIELDS = ["时间", "产品", "季节", "风格", "文案"]


# ---------- 生成文案（和 09 一样，不用你改） ----------

def build_prompt(product, season, style):
    return f"""你是咖啡品牌文案专家。为「暖爪咖啡 WARM PAW」的{season}新品「{product}」写 3 组小红书文案。
风格：{style}。
每组包含：主标题、副标题、品牌 slogan（暖爪捧杯 快乐翻倍）、3 个卖点关键词。
只输出文案，不要解释。"""


def call_ai(prompt):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


# ---------- 记账（今天新学的部分，你要填 3 个空） ----------

def append_history(product, season, style, content):
    """往 历史记录.csv 追加一行。文件不存在就先写表头。"""
    is_new_file = not HISTORY_FILE.exists()

    # "a" 是 append 模式：只往后加，不覆盖以前的内容
    with HISTORY_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        if is_new_file:
            writer.writeheader()

        row = {
            # TODO 1：这里填「当前时间」，格式要像 2026-11-18 14:30
            # 提示：datetime.now().strftime("%Y-%m-%d %H:%M")
            "时间":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "产品": product,
            "季节": season,
            "风格": style,
            "文案": content,
        }

        # TODO 2：把上面这行 row 真正写进文件里
        # 提示：writer.writerow(row)
        writer.writerow(row)

def query_history(keyword):
    """列出产品名里包含 keyword 的所有历史版本。"""
    if not HISTORY_FILE.exists():
        print("还没有历史记录，先选菜单 1 生成一条吧。")
        return

    with HISTORY_FILE.open("r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    matched = []
    for row in rows:
        # TODO 3：如果这一行的产品名里包含 keyword，就把 row 收进 matched
        # 提示：if keyword in row["产品"]:
        #           matched.append(row)
        if keyword in row["产品"]:
            matched.append(row)

    if not matched:
        print(f"没找到包含「{keyword}」的记录。")
        return

    print(f"\n找到 {len(matched)} 条记录：")
    for row in matched:
        print("-" * 50)
        print(f"时间：{row['时间']}")
        print(f"产品：{row['产品']}｜季节：{row['季节']}｜风格：{row['风格']}")
        print(f"文案：{row['文案'][:100]}")


# ---------- 主流程 ----------

def main():
    print("=" * 50)
    print("  暖爪咖啡 · 文案工具 v3（会记账）")
    print("=" * 50)
    print("1 = 生成新文案，并记进历史记录")
    print("2 = 查某个产品以前写过哪些版本")
    choice = input("请选择（1/2）：").strip()

    if choice == "2":
        keyword = input("输入产品名关键词：").strip()
        query_history(keyword)
    else:
        product = input("产品名：").strip()
        season = input("季节（秋日/冬日/春日/夏日）：").strip()
        style = input("风格（极简风/治愈系/复古风/高级感/国风）：").strip()

        print("\n正在生成...")
        content = call_ai(build_prompt(product, season, style))
        print(content)

        append_history(product, season, style, content)
        print("\n已记入 历史记录.csv")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()

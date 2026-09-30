#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将指定文件夹中的图像文件批量重命名为连续编号（后缀保持不变）。

两种编号模式:

1) 默认模式 (跳过冲突, 可能留空洞)
   遇到目标编号已被占用(可能是待处理文件)时, 直接向后递增, 用下一个空闲编号。
   实现简单、安全, 但最终编号可能不连续(会跳过被占用的号码)。

2) 强制连续模式 (--consecutive, 无空洞)
   第 k 个文件的目标位固定等于"起始号 + k", 编号 100% 无缝连续。
   做法: 先把"当前名字恰好是别人目标位"的冲突文件改名到一个唯一临时名(腾位),
        等所有目标位空闲后, 再逐个改写为其最终目标名(落位)。
   全程绝不覆盖、不丢失任何文件。

用法示例:
    python rename_images.py                              # 预览(当前文件夹, 默认跳号模式)
    python rename_images.py --apply                      # 真正执行
    python rename_images.py --consecutive --apply        # 强制连续编号 + 真正执行
    python rename_images.py --start 10345 --consecutive "D:/照片"
    python rename_images.py --start 1 --apply --recursive --consecutive --ext .heic "C:/pics"

安全保证（很重要）:
- 脚本中不存在任何"删除/清空"操作(os.remove / unlink / shutil.rmtree)。文件只会被
  os.rename 改成另一个名字, 源文件永远不会消失——最坏只是跑到别的名字/临时名下。
- 每次改写前都确认目标位不存在(绝不覆盖已有文件); Windows 上 os.rename 对已存在
  目标还会再报错拒改, 形成第二道防线。
- 执行前把"要做的所有改名"预先排好计划并校验; --apply 前仍先打印整个计划。
- 执行时逐条记录日志; 一旦中途出错, 会尝试把已做的改名逆序回滚, 尽量恢复原状。
- 崩溃/断电这种不可抗力无法 100% 避免, 但不会删文件, 且有日志可供人工恢复。
"""

import os
import re
import sys

# 保证中文输出在 Windows 终端(或重定向文件)下正常显示
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".webp", ".tiff", ".tif", ".ico", ".jfif",
}


class RenameError(Exception):
    pass


def natural_key(name):
    """把文件名里的数字按数值拆开, 实现 '10' 排在 '9' 之前的自然排序。"""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", name)]


def collect_images(root, ext_set, recursive):
    matching = []
    if recursive:
        for dirpath, _dirs, filenames in os.walk(root):
            for f in filenames:
                if os.path.splitext(f)[1].lower() in ext_set:
                    matching.append(os.path.join(dirpath, f))
    else:
        for f in os.listdir(root):
            path = os.path.join(root, f)
            if os.path.isfile(path) and os.path.splitext(f)[1].lower() in ext_set:
                matching.append(path)
    return matching


def pick_free(tmp_box, ddir, ext, reserved):
    """生成目录里不存在的唯一临时文件名(用于腾位)。"""
    while True:
        tmp_name = f".__room_{os.getpid()}_{tmp_box[0]}{ext}"
        tmp_box[0] += 1
        if not os.path.exists(os.path.join(ddir, tmp_name)) and tmp_name not in reserved:
            return os.path.join(ddir, tmp_name)


def build_plan(files, start, consecutive):
    """
    把这次重命名预先排成一张"计划"(moves: src 绝对路径 -> dst 绝对路径)。
    不触碰磁盘, 只是计算要做的每一条改名。
    返回 (moves, extras) ；extras 是腾位动作的文字说明(用于预览)。
    """
    moves = []          # 顺序执行即可; 回滚时逆序
    notes = []          # 预览用的人类可读说明
    reserved = set()

    if consecutive:
        pairs = []
        for idx, path in enumerate(files):
            _base, ext = os.path.splitext(os.path.basename(path))
            dst = os.path.join(os.path.dirname(path), f"{start + idx}{ext}")
            pairs.append((path, ext, dst))
            reserved.add(os.path.basename(dst))

        dest_names = {os.path.basename(dst) for _, _, dst in pairs}
        tmp_box = [0]
        temps = {}      # path -> temp   (阶段1被腾位的)

        # 阶段1: 腾位(先把占着别人目标位的挪到临时名)
        for src, ext, dst in pairs:
            cur = os.path.basename(src)
            if cur in dest_names and cur != os.path.basename(dst):
                temp = pick_free(tmp_box, os.path.dirname(src), ext, dest_names)
                temps[src] = temp
                moves.append((src, temp))
                notes.append(f"  [先让位] {cur}  ->  临时 ->  {os.path.basename(dst)}")

        # 阶段2: 落位(目标位已空闲, 各就各位)
        for src, ext, dst in pairs:
            cur = temps.get(src, src)
            if os.path.abspath(cur) == os.path.abspath(dst):
                continue                                   # 本就就位, 不动
            moves.append((cur, dst))
            notes.append(f"  {os.path.basename(src)}  ->  {os.path.basename(dst)}")
    else:
        counter = start
        for path in files:
            fdir = os.path.dirname(path)
            _base, ext = os.path.splitext(os.path.basename(path))
            while os.path.exists(os.path.join(fdir, str(counter) + ext)):
                counter += 1                               # 探测下一个空闲号
            dst = os.path.join(fdir, f"{counter}{ext}")
            counter += 1
            if os.path.abspath(path) != os.path.abspath(dst):
                moves.append((path, dst))
                notes.append(f"  {os.path.basename(path)}  ->  {os.path.basename(dst)}")

    return moves, notes


def validate_plan(moves):
    """
    执行前静默自检: 以磁盘真实状态为初态, 按计划顺序"模拟"每一步改名,
    逐步确认目标位不存在(绝不覆盖)。

    必须按顺序模拟而不能逐条直接查磁盘: --consecutive 计划是"先腾位、后落位"
    两阶段的, 落位阶段的某些目标位此刻仍被占, 要等前面的腾位动作执行后才会空。
    有隐患则抛出 RenameError, 让 main 中止——在触碰任何文件之前就停下来。
    """
    state = {}      # 目录 -> 该目录当前(模拟状态下)的文件名集合
    for src, dst in moves:
        dsrc, sname = os.path.split(src)
        ddst, dname = os.path.split(dst)
        for d in (dsrc, ddst):
            if d not in state:
                try:
                    state[d] = set(os.listdir(d))
                except FileNotFoundError:
                    state[d] = set()

        if os.path.abspath(src) == os.path.abspath(dst):
            continue                                       # 自身改名, 安全
        if sname not in state[dsrc]:
            raise RenameError(
                f"[预检拦截] 计划执行到该步时源文件已不在, 已中止:\n    源文件: {src}"
            )
        if dname in state[ddst]:
            raise RenameError(
                f"[预检拦截] 目标位已存在, 拒绝覆盖:\n    原文件: {src}\n    目标位: {dst}"
            )
        # 模拟这一步改名: 从源目录移除, 加入目标目录
        state[dsrc].discard(sname)
        state[ddst].add(dname)


def safe_apply(moves, journal):
    """
    真正执行改动, 并具备逐条回滚能力。
    - 每步在动手前再次确认目标位空闲(os.rename 在 Windows 上对已存在目标也会拒绝)。
    - 每成功一步就写入 journal 日志; 出错则逆序回滚已做的改动, 尽量恢复原状。
    - 永不调用删除操作: 文件只会改名, 不会消失。
    """
    performed = []   # [(src, dst), ...]
    try:
        for src, dst in moves:
            if os.path.abspath(src) == os.path.abspath(dst):
                continue
            if os.path.exists(dst):
                raise RenameError(f"目标位已存在, 拒绝覆盖: {dst}")
            os.rename(src, dst)
            performed.append((src, dst))
            with open(journal, "a", encoding="utf-8") as fh:
                fh.write(f"{src} -> {dst}\n")
    except Exception as exc:
        print(f"\n!! 中途出错: {exc}")
        print("正在尝试回滚已完成的改动……")
        rolled = 0
        for src, dst in reversed(performed):
            try:
                os.rename(dst, src)
                rolled += 1
            except Exception as rex:
                print(f"回滚失败( {src} <-> {dst} ): {rex}")
        print(f"已回滚 {rolled}/{len(performed)} 步。日志见: {journal}")
        raise
    return len(performed)


def main():
    start = 10345
    folder = "."
    apply = False
    recursive = False
    consecutive = False

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--start":
            start = int(argv[i + 1]); i += 2
        elif a == "--apply":
            apply = True; i += 1
        elif a == "--consecutive":
            consecutive = True; i += 1
        elif a == "--recursive":
            recursive = True; i += 1
        elif a == "--ext":
            ext = argv[i + 1].lower()
            if not ext.startswith("."):
                ext = "." + ext
            IMAGE_EXTS.add(ext); i += 2
        else:
            folder = a; i += 1

    root = os.path.abspath(folder)
    files = collect_images(root, IMAGE_EXTS, recursive)
    files.sort(key=lambda p: natural_key(os.path.basename(p)))

    if not files:
        print("未找到任何符合条件的图像文件。")
        return

    mode = ("强制连续(--consecutive)" if consecutive else "默认(跳号)")
    phase = "APPLY(实际执行)" if apply else "DRY-RUN(仅预览)"
    print(f"目标文件夹: {root}")
    print(f"共 {len(files)} 个图像文件, 起始编号 {start}, 模式: {mode}, 状态: {phase}\n")

    moves, notes = build_plan(files, start, consecutive)

    # 预览: 只打印, 绝不碰盘
    for line in notes:
        print(line)

    if not apply:
        n = len(moves)
        print(f"\n以上为 {n} 条待执行的改名(仅预览, 未改动任何文件)。")
        print("确认无误后, 加 --apply 再运行一次即可真正执行。")
        return

    # 真正执行前: 二次自检
    validate_plan(moves)
    journal = os.path.join(root, f".rename_log_{os.getpid()}.txt")
    done = safe_apply(moves, journal)
    print(f"\n✅ 已执行 {done} 条改名, 完成。")
    print(f"变更日志(便于核对/恢复): {journal}")


if __name__ == "__main__":
    main()
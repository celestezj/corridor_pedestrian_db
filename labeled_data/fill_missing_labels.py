# -*- coding: utf-8 -*-
"""为缺失标签文件的图像创建空的标签文件。

只处理"有图像、但对应标签文件缺失"的情况：为这些图像创建一个空的 .txt。
严禁修改或删除任何已有的图像/标签文件。
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(BASE, "frames")
LABELS = os.path.join(BASE, "labels")

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}  # 图像扩展名，按需调整


def main():
    if not os.path.isdir(FRAMES):
        sys.exit(f"[错误] 找不到 frames 目录: {FRAMES}")
    os.makedirs(LABELS, exist_ok=True)  # labels 不存在时创建（不触碰已有内容）

    missing = []
    for fname in sorted(os.listdir(FRAMES)):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in IMG_EXTS:
            continue  # 非图像文件，跳过
        lbl = os.path.join(LABELS, stem + ".txt")
        if not os.path.exists(lbl):
            missing.append((fname, lbl))

    created = 0
    for img, lbl in missing:
        try:
            with open(lbl, "w", encoding="utf-8") as f:
                pass  # 写空文件
            created += 1
            print(f"[已补齐] {os.path.basename(img)} -> {os.path.relpath(lbl, BASE)}")
        except OSError as e:
            print(f"[失败] {os.path.basename(img)}: {e}")

    print("-" * 40)
    print(f"检查图像: {len(os.listdir(FRAMES))} 个 | 缺失标签: {len(missing)} 个 | 已创建空标签: {created} 个")
    if created == 0:
        print("没有缺失的标签文件，无需改动。")


if __name__ == "__main__":
    main()
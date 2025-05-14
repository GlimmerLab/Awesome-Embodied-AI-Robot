#!/usr/bin/env python3
import os
import shutil
import yaml
import json
from datetime import datetime
import re

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

def backup_important_files():
    """备份重要的文件以防被覆盖"""
    print("备份重要文件...")
    backup_dir = "_backup_docs"
    ensure_dir(backup_dir)

    # 需要备份的文件列表
    important_files = [
        "docs/index.md",
        "docs/index_cn.md",
        "docs/index_en.md",
        "docs/_config.yml",
        "docs/assets/css/style.scss",
        "docs/_layouts/default.html"
    ]

    for file_path in important_files:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"  已备份: {file_path} -> {backup_path}")

    print("备份完成")

def restore_important_files():
    """恢复重要的文件以防被覆盖"""
    print("恢复重要文件...")
    backup_dir = "_backup_docs"

    if not os.path.exists(backup_dir):
        print("  未找到备份目录，跳过恢复")
        return

    # 需要恢复的文件列表
    restore_files = [
        ("index.md", "docs/index.md"),
        ("index_cn.md", "docs/index_cn.md"),
        ("index_en.md", "docs/index_en.md"),
        ("_config.yml", "docs/_config.yml"),
        ("style.scss", "docs/assets/css/style.scss"),
        ("default.html", "docs/_layouts/default.html")
    ]

    for backup_file, restore_path in restore_files:
        backup_path = os.path.join(backup_dir, backup_file)
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, restore_path)
            print(f"  已恢复: {backup_path} -> {restore_path}")

    print("恢复完成")

def clean_docs_dir():
    """清理 docs 目录，只删除内容文件但保留结构和设计文件"""
    if os.path.exists("docs"):
        # 保留这些文件和目录
        keep_files = {
            "_config.yml",
            "_layouts",
            "_includes",
            "assets",
            "index.md",
            "index_en.md",
            "index_cn.md",
            "favicon.ico",
            "CNAME",
            "404.html",
            "robots.txt",
            "sitemap.xml"
        }

        # 删除分类内容文件，但保留网站结构文件
        for item in os.listdir("docs"):
            if item not in keep_files:
                path = os.path.join("docs", item)
                if os.path.isfile(path) and (
                    item.endswith('.md') and
                    not item in ['index.md', 'index_en.md', 'index_cn.md']
                ):
                    os.remove(path)
                    print(f"  删除文件: {path}")
        print("已选择性清理 docs 目录")

def add_front_matter(content, title, description, category=None, lang="en"):
    """添加Jekyll前置元数据"""
    front_matter = f"""---
layout: default
title: {title}
description: {description}
"""

    if category:
        front_matter += f"category: {category}\n"

    front_matter += f"lang: {lang}\n"
    front_matter += f"last_updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    front_matter += "---\n\n"

    return front_matter + content

def sync_readme_files():
    # 源目录和目标目录
    categories = {
        "Fundamental-Theory": {
            "id": "fundamental_theory",
            "en": "Fundamental Theory",
            "cn": "基础理论",
            "description_en": "Core theoretical foundations of embodied AI",
            "description_cn": "具身智能的核心理论基础",
            "icon": "book"
        },
        "Robot-Learning-and-Reinforcement-Learning": {
            "id": "robot_learning_and_reinforcement_learning",
            "en": "Robot Learning and Reinforcement Learning",
            "cn": "机器人学习与强化学习",
            "description_en": "Papers on robot learning and reinforcement learning",
            "description_cn": "机器人学习和强化学习相关论文",
            "icon": "robot"
        },
        "Environment-Perception": {
            "id": "environment_perception",
            "en": "Environment Perception",
            "cn": "环境感知",
            "description_en": "Research on environment perception in embodied AI",
            "description_cn": "具身智能中的环境感知研究",
            "icon": "camera"
        },
        "Motion-Planning": {
            "id": "motion_planning",
            "en": "Motion Planning",
            "cn": "运动规划",
            "description_en": "Motion planning algorithms and implementations",
            "description_cn": "运动规划算法与实现",
            "icon": "map"
        },
        "Task-Planning": {
            "id": "task_planning",
            "en": "Task Planning",
            "cn": "任务规划",
            "description_en": "Task planning and execution in embodied AI",
            "description_cn": "具身智能中的任务规划与执行",
            "icon": "list-task"
        },
        "Multimodal-Interaction": {
            "id": "multimodal_interaction",
            "en": "Multimodal Interaction",
            "cn": "多模态交互",
            "description_en": "Multimodal interaction research in embodied AI",
            "description_cn": "具身智能中的多模态交互研究",
            "icon": "chat-dots"
        },
        "Simulation-Platforms": {
            "id": "simulation_platforms",
            "en": "Simulation Platforms",
            "cn": "仿真平台",
            "description_en": "Simulation platforms for embodied AI research",
            "description_cn": "具身智能研究的仿真平台",
            "icon": "pc-display"
        }
    }

    # 确保docs目录存在
    ensure_dir("docs")

    # 同步每个分类的README文件
    for src_dir, info in categories.items():
        if os.path.exists(src_dir):
            print(f"处理目录: {src_dir}")

            # 同步英文README
            if os.path.exists(f"{src_dir}/README.md"):
                with open(f"{src_dir}/README.md", "r", encoding="utf-8") as f:
                    content = f.read()

                # 添加前置元数据
                content = add_front_matter(
                    content,
                    info["en"],
                    info["description_en"],
                    info["id"],
                    "en"
                )

                # 增强内容
                content = enhance_content(content, info, "en")

                dst_file = f"docs/{info['id']}.md"
                with open(dst_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"已同步 {src_dir}/README.md 到 {dst_file}")

            # 同步中文README
            if os.path.exists(f"{src_dir}/README_CN.md"):
                with open(f"{src_dir}/README_CN.md", "r", encoding="utf-8") as f:
                    content = f.read()

                # 添加前置元数据
                content = add_front_matter(
                    content,
                    info["cn"],
                    info["description_cn"],
                    info["id"],
                    "zh"
                )

                # 增强内容
                content = enhance_content(content, info, "zh")

                dst_file = f"docs/{info['id']}_cn.md"
                with open(dst_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"已同步 {src_dir}/README_CN.md 到 {dst_file}")

def enhance_content(content, category_info, lang):
    """增强Markdown内容，添加更好的显示效果"""
    # 为第一个标题添加图标
    icon = category_info.get("icon", "book")
    title_text = category_info['en'] if lang == 'en' else category_info['cn']

    # 查找第一个标题并替换
    pattern = r'^# (.+)$'
    replacement = f'# <i class="bi bi-{icon}"></i> {title_text}'
    content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    # 为表格添加Bootstrap样式
    content = re.sub(r'<table>', '<table class="table table-striped table-hover table-responsive">', content)
    content = re.sub(r'\|\s*--+\s*\|', '| :--- |', content)  # 修复Markdown表格格式

    # 不替换链接，保留Markdown链接格式以兼容Jekyll处理
    # content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', content)

    # 添加更新日期信息
    update_info = "最后更新: " if lang == "zh" else "Last updated: "
    update_info += datetime.now().strftime('%Y-%m-%d')
    content += f"\n\n<p class='text-muted text-end'><small>{update_info}</small></p>"

    return content

def create_index_files():
    """保持现有索引文件，不重新创建"""
    # 创建英文和中文的索引文件
    # 已在专门的HTML文件中创建，这里不需要修改
    print("保留现有索引文件结构")

def generate_sitemap():
    """生成网站地图"""
    print("生成sitemap.xml...")
    site_base_url = "https://glimmerlab.github.io/Awesome-Embodied-AI"

    files = []
    for root, _, filenames in os.walk("docs"):
        for filename in filenames:
            if filename.endswith('.md') or filename.endswith('.html'):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, "docs")
                # 将index.md转换为/
                if rel_path == "index.md":
                    url_path = "/"
                else:
                    url_path = "/" + rel_path.replace('.md', '.html')

                files.append({
                    "url": site_base_url + url_path,
                    "lastmod": datetime.now().strftime('%Y-%m-%d')
                })

    # 生成XML
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for f in files:
        xml.append('  <url>')
        xml.append(f'    <loc>{f["url"]}</loc>')
        xml.append(f'    <lastmod>{f["lastmod"]}</lastmod>')
        xml.append('    <changefreq>weekly</changefreq>')
        xml.append('  </url>')

    xml.append('</urlset>')

    # 写入文件
    with open("docs/sitemap.xml", "w", encoding="utf-8") as f:
        f.write('\n'.join(xml))
    print("sitemap.xml生成完成")

def ensure_assets():
    """确保静态资源存在"""
    # 确保assets目录存在
    assets_dir = "docs/assets"
    ensure_dir(assets_dir)

    # 确保css目录存在
    css_dir = os.path.join(assets_dir, "css")
    ensure_dir(css_dir)

    # 确保images目录存在
    images_dir = os.path.join(assets_dir, "images")
    ensure_dir(images_dir)

    # 确保favicon存在
    if not os.path.exists("docs/favicon.ico") and os.path.exists("docs/assets/images/favicon.png"):
        shutil.copy("docs/assets/images/favicon.png", "docs/favicon.ico")
        print("已创建favicon.ico")

    # 创建robots.txt
    if not os.path.exists("docs/robots.txt"):
        with open("docs/robots.txt", "w", encoding="utf-8") as f:
            f.write("User-agent: *\nAllow: /\nSitemap: https://glimmerlab.github.io/Awesome-Embodied-AI/sitemap.xml")
        print("已创建robots.txt")

    # 创建404页面
    if not os.path.exists("docs/404.html"):
        with open("docs/404.html", "w", encoding="utf-8") as f:
            f.write("""---
layout: default
title: 404 - 页面未找到
description: 抱歉，您请求的页面不存在
lang: zh
---

<div class="text-center my-5">
  <h1><i class="bi bi-emoji-frown"></i> 404</h1>
  <h3>抱歉，您请求的页面不存在</h3>
  <p class="mb-4">可能是链接已经更改或输入的网址有误</p>
  <div class="my-4">
    <a href="{{ site.baseurl }}/" class="btn btn-primary me-2"><i class="bi bi-house-door"></i> 返回首页</a>
    <a href="https://github.com/LJoson/Awesome-Embodied-AI/issues" class="btn btn-outline-secondary"><i class="bi bi-bug"></i> 报告问题</a>
  </div>
</div>
""")
        print("已创建404.html")

def check_page_modifications():
    """检查是否有修改过的页面需要保留"""
    print("检查页面修改...")
    modified_files = []

    # 检查index文件
    index_files = ["docs/index.md", "docs/index_cn.md", "docs/index_en.md"]
    for file_path in index_files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否包含我们的卡片式布局特征
            if "<div class=\"row mb-5\">" in content and "<div class=\"card" in content:
                modified_files.append(file_path)
                print(f"  发现修改过的文件: {file_path}")

    return modified_files

def main():
    print("开始同步文档...")

    # 备份重要文件
    backup_important_files()

    # 检查自定义修改
    modified_files = check_page_modifications()
    if modified_files:
        print(f"发现 {len(modified_files)} 个已优化的文件，将保留这些修改")

    clean_docs_dir()   # 首先清理 docs 目录
    ensure_assets()    # 确保静态资源文件夹存在
    sync_readme_files()
    create_index_files()
    generate_sitemap() # 生成网站地图

    # 恢复重要文件
    restore_important_files()

    # 列出docs目录中的所有文件
    print("\ndocs目录中的文件:")
    for root, dirs, files in os.walk("docs"):
        rel_path = os.path.relpath(root, "docs")
        if rel_path == ".":
            path_prefix = ""
        else:
            path_prefix = rel_path + "/"

        for file in sorted(files):
            print(f"  {path_prefix}{file}")

    print("\n文档同步完成！请通过GitHub Actions部署更新后的网站。")

if __name__ == "__main__":
    main()
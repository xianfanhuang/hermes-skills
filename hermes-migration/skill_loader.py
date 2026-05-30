#!/usr/bin/env python3
"""
Hermes Skills Loader - 双轨制技能加载器
新环境按需从GitHub拉取技能

用法：
    python3 skill_loader.py [--repo https://github.com/vanwoung/hermes-skills] [--all|--skill skill_name]
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/vanwoung/hermes-skills.git"
SKILLS_DIR = "./skills"

def find_manifest():
    """智能查找skill-manifest.json"""
    # 尝试多个可能的位置
    possible_paths = [
        "./skill-manifest.json",
        "../skill-manifest.json",
        "../../skill-manifest.json",
        "./hermes-export/hermes-portable-*/skill-manifest.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
        # 支持通配符
        if "*" in path:
            import glob
            matches = glob.glob(path)
            if matches:
                return matches[0]  # 返回第一个匹配
    
    return None

def load_skill_manifest():
    """读取当前环境的skill-manifest.json"""
    manifest_path = find_manifest()
    if manifest_path:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def clone_skill_repo(repo_url, temp_dir="./.hermes-temp"):
    """克隆技能仓库到临时目录"""
    print(f"📥 克隆技能仓库: {repo_url}")
    if os.path.exists(temp_dir):
        subprocess.run(["rm", "-rf", temp_dir], check=False)
    
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, temp_dir],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ 克隆失败: {result.stderr}")
        return None
    
    print(f"✅ 仓库克隆成功")
    return temp_dir

def install_skill(skill_name, source_dir, target_dir="./skills"):
    """安装单个技能"""
    source_path = os.path.join(source_dir, skill_name)
    target_path = os.path.join(target_dir, skill_name)
    
    if not os.path.exists(source_path):
        print(f"❌ 技能不存在: {skill_name}")
        return False
    
    # 如果已存在，备份旧版本
    if os.path.exists(target_path):
        backup_path = f"{target_path}.backup"
        subprocess.run(["rm", "-rf", backup_path], check=False)
        os.rename(target_path, backup_path)
        print(f"📦 已备份旧版本: {skill_name}.backup")
    
    # 复制新版本
    subprocess.run(["cp", "-r", source_path, target_path], check=True)
    print(f"✅ 已安装: {skill_name}")
    return True

def load_skills(repo_url=None, skill_name=None, all_skills=False):
    """
    加载技能
    
    Args:
        repo_url: GitHub仓库地址
        skill_name: 指定加载单个技能
        all_skills: 是否加载manifest中所有技能
    """
    # 读取manifest
    manifest = load_skill_manifest()
    if not manifest:
        print("❌ 未找到skill-manifest.json，请先执行hermes导出")
        return False
    
    # 克隆仓库
    repo_url = repo_url or manifest.get("github_repo", REPO_URL)
    temp_dir = clone_skill_repo(repo_url)
    if not temp_dir:
        return False
    
    # 确定要加载的技能
    skills_to_load = []
    if skill_name:
        skills_to_load = [skill_name]
    elif all_skills:
        skills_to_load = [s["name"] for s in manifest.get("skills", [])]
    else:
        # 默认加载required技能
        skills_to_load = [s["name"] for s in manifest.get("skills", []) if s.get("required")]
    
    print(f"\n📦 准备加载 {len(skills_to_load)} 个技能...")
    
    # 安装技能
    success_count = 0
    for name in skills_to_load:
        if install_skill(name, temp_dir):
            success_count += 1
    
    # 清理临时目录
    subprocess.run(["rm", "-rf", temp_dir], check=False)
    
    print(f"\n{'='*60}")
    print(f"✅ 加载完成: {success_count}/{len(skills_to_load)} 个技能")
    print(f"{'='*60}")
    
    return success_count == len(skills_to_load)

def list_available_skills():
    """列出manifest中可用的技能"""
    manifest = load_skill_manifest()
    if not manifest:
        print("❌ 未找到skill-manifest.json")
        return
    
    print("\n📋 可用技能清单：")
    print(f"{'='*60}")
    print(f"{'名称':<30} {'版本':<10} {'优先级':<8} {'必需':<6}")
    print(f"{'-'*60}")
    
    for skill in manifest.get("skills", []):
        name = skill["name"][:28]
        version = skill.get("version", "unknown")[:8]
        priority = str(skill.get("priority", 0))
        required = "✓" if skill.get("required") else ""
        print(f"{name:<30} {version:<10} {priority:<8} {required:<6}")
    
    print(f"{'='*60}")
    print(f"总计: {len(manifest.get('skills', []))} 个技能")

def main():
    parser = argparse.ArgumentParser(description="Hermes Skills Loader - 双轨制技能加载器")
    parser.add_argument("--repo", help="GitHub仓库地址")
    parser.add_argument("--skill", help="加载指定技能")
    parser.add_argument("--all", action="store_true", help="加载所有技能")
    parser.add_argument("--list", action="store_true", help="列出可用技能")
    
    args = parser.parse_args()
    
    if args.list:
        list_available_skills()
    elif args.skill:
        load_skills(repo_url=args.repo, skill_name=args.skill)
    elif args.all:
        load_skills(repo_url=args.repo, all_skills=True)
    else:
        # 默认加载required技能
        load_skills(repo_url=args.repo)

if __name__ == "__main__":
    main()

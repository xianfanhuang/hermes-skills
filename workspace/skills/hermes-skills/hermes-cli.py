#!/usr/bin/env python3
"""
Hermes CLI - 双轨制技能管理工具
跨平台通用，支持技能加载、清单查看、版本管理

用法：
    python3 hermes-cli.py [command] [options]

命令：
    load-required       加载必需技能（默认）
    load-all            加载所有技能
    load SKILL_NAME     加载指定技能
    list                列出可用技能
    export              导出核心层迁移包
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

REPO_URL = "https://github.com/xianfanhuang/hermes-skills.git"
SKILLS_DIR = "./skills"

def find_manifest():
    """查找skill-manifest.json"""
    paths = ["./skill-manifest.json", "../skill-manifest.json", "./hermes-core/skill-manifest.json"]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def load_manifest():
    """加载manifest"""
    path = find_manifest()
    if path:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def cmd_list():
    """列出技能"""
    manifest = load_manifest()
    if not manifest:
        print("❌ 未找到 skill-manifest.json")
        print("   请先执行: python3 hermes-cli.py export")
        return 1
    
    print("\n📋 Hermes Skills 清单")
    print("=" * 60)
    print(f"{'名称':<30} {'版本':<10} {'优先级':<8} {'必需':<6}")
    print("-" * 60)
    
    for skill in manifest.get("skills", []):
        name = skill["name"][:28]
        version = skill.get("version", "unknown")[:8]
        priority = str(skill.get("priority", 0))
        required = "✓" if skill.get("required") else ""
        print(f"{name:<30} {version:<10} {priority:<8} {required:<6}")
    
    print("=" * 60)
    print(f"总计: {len(manifest.get('skills', []))} 个技能")
    print(f"仓库: {manifest.get('github_repo', REPO_URL)}")
    return 0

def cmd_load(skill_name=None, load_required=False, load_all=False):
    """加载技能"""
    manifest = load_manifest()
    if not manifest:
        print("❌ 未找到 skill-manifest.json")
        return 1
    
    # 确定要加载的技能
    to_load = []
    if skill_name:
        to_load = [skill_name]
    elif load_required:
        to_load = [s["name"] for s in manifest.get("skills", []) if s.get("required")]
    elif load_all:
        to_load = [s["name"] for s in manifest.get("skills", [])]
    
    if not to_load:
        print("⚠️ 没有要加载的技能")
        return 0
    
    print(f"\n📦 准备加载 {len(to_load)} 个技能...")
    
    # 克隆仓库到临时目录
    temp_dir = ".hermes-temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    repo = manifest.get("github_repo", REPO_URL)
    print(f"📥 克隆仓库: {repo}")
    
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo, temp_dir],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"❌ 克隆失败: {result.stderr}")
        return 1
    
    # 安装技能
    os.makedirs(SKILLS_DIR, exist_ok=True)
    success = 0
    
    for name in to_load:
        src = os.path.join(temp_dir, name)
        dst = os.path.join(SKILLS_DIR, name)
        
        if not os.path.exists(src):
            print(f"⚠️ 仓库中未找到: {name}")
            continue
        
        # 备份旧版本
        if os.path.exists(dst):
            backup = f"{dst}.backup"
            if os.path.exists(backup):
                shutil.rmtree(backup)
            os.rename(dst, backup)
        
        # 复制新版本
        shutil.copytree(src, dst)
        print(f"✅ 已加载: {name}")
        success += 1
    
    # 清理
    shutil.rmtree(temp_dir)
    
    print(f"\n{'='*60}")
    print(f"✅ 加载完成: {success}/{len(to_load)} 个技能")
    print(f"{'='*60}")
    return 0 if success == len(to_load) else 1

def main():
    parser = argparse.ArgumentParser(description="Hermes CLI - 双轨制技能管理")
    parser.add_argument("command", nargs="?", default="list", 
                       choices=["list", "load", "load-required", "load-all", "export"],
                       help="命令")
    parser.add_argument("--skill", help="指定技能名称")
    parser.add_argument("--repo", help="自定义仓库地址")
    
    args = parser.parse_args()
    
    if args.command == "list":
        return cmd_list()
    elif args.command == "load":
        return cmd_load(skill_name=args.skill)
    elif args.command == "load-required":
        return cmd_load(load_required=True)
    elif args.command == "load-all":
        return cmd_load(load_all=True)
    elif args.command == "export":
        print("请使用: python3 ./skills/hermes-migration/export_hermes.py")
        return 0
    else:
        return cmd_list()

if __name__ == "__main__":
    sys.exit(main())

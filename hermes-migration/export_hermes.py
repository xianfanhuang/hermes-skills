#!/usr/bin/env python3
"""
Hermes Migration - 导出脚本
将核心灵魂文件打包为可迁移格式

使用方法：
    python3 export_hermes.py [--output-dir ./hermes-export]
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

def get_timestamp():
    """生成时间戳"""
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def create_manifest(timestamp, source_files, projects):
    """创建manifest.json"""
    return {
        "version": "1.0",
        "timestamp": timestamp,
        "created_at": datetime.now().isoformat(),
        "source_platform": "Coze OpenClaw",
        "target_platforms": ["MiMo Claw", "Other"],
        "files": {
            "core": ["SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"],
            "experience": ["TOOLS.md"],
            "instruction": ["00-INSTRUCTION.md"]
        },
        "source_files": source_files,
        "projects": projects,
        "excluded": [
            "SECRET.md (敏感凭证，需手动配置)",
            "实时session状态",
            "临时文件和缓存",
            "skills/目录 (双轨制，独立管理)"
        ],
        "notes": [
            "此包包含Hermes的灵魂层和经验层",
            "SECRET.md因安全原因不包含，需在新平台重新配置",
            "Skills采用双轨制管理，见 skill-manifest.json",
            "建议每日同步关键记忆更新"
        ]
    }

def create_skill_manifest():
    """创建skill-manifest.json - 双轨制技能清单"""
    skills_dir = "./skills"
    skills = []
    
    if os.path.exists(skills_dir):
        for item in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, item)
            if os.path.isdir(skill_path):
                # 读取SKILL.md获取版本信息
                skill_md = os.path.join(skill_path, "SKILL.md")
                version = "unknown"
                if os.path.exists(skill_md):
                    try:
                        with open(skill_md, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith("version:"):
                                    version = line.split(":")[1].strip()
                                    break
                    except:
                        pass
                
                skills.append({
                    "name": item,
                    "version": version,
                    "priority": get_skill_priority(item),
                    "required": item in ["hermes-migration", "token-budget-manager"]
                })
    
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "github_repo": "https://github.com/vanwoung/hermes-skills",
        "load_strategy": "on_demand",
        "skills": sorted(skills, key=lambda x: x["priority"], reverse=True)
    }

def get_skill_priority(skill_name):
    """获取技能优先级（高优先级先加载）"""
    priority_map = {
        "hermes-migration": 100,      # 迁移系统最高优先级
        "token-budget-manager": 90,   # 预算管理
        "lark_cli": 80,               # 飞书操作
        "contract-review": 70,
        "excel_master": 60,
        "docx": 50,
        "pdf": 40,
        # 其他默认0
    }
    return priority_map.get(skill_name, 0)

def copy_file(src, dst, dry_run=False):
    """复制文件，支持dry-run模式"""
    if dry_run:
        print(f"[DRY-RUN] 将复制: {src} -> {dst}")
        return True
    
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f"✅ 已复制: {src}")
        return True
    except Exception as e:
        print(f"❌ 复制失败 {src}: {e}")
        return False

def get_projects_list():
    """获取项目列表"""
    projects = []
    # 检查常见的项目目录
    possible_paths = [
        "./OpenClaw生态",
        "./First-Mate交易系统",
        "./长期计划",
        "./AI-and-Trading",
        "./projects"
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            projects.append(path)
    
    return projects

def find_project_root():
    """智能查找项目根目录"""
    current = os.getcwd()
    
    # 如果在skills/hermes-migration下，向上两级
    if "skills/hermes-migration" in current or "skills\\hermes-migration" in current:
        return os.path.abspath(os.path.join(current, "../.."))
    
    # 检查当前目录是否有USER.md等核心文件
    if os.path.exists("./USER.md") and os.path.exists("./基础设定/SOUL.md"):
        return current
    
    # 默认返回当前目录
    return current

def export_hermes(output_dir="./hermes-export", dry_run=False):
    """
    导出Hermes迁移包
    
    Args:
        output_dir: 输出目录
        dry_run: 是否只打印预览，不实际执行
    """
    # 智能定位项目根目录
    project_root = find_project_root()
    os.chdir(project_root)
    
    timestamp = get_timestamp()
    package_name = f"hermes-portable-{timestamp}"
    package_dir = os.path.join(output_dir, package_name)
    
    print(f"{'='*60}")
    print(f"Hermes Migration Export")
    print(f"{'='*60}")
    print(f"项目根目录: {project_root}")
    print(f"输出目录: {package_dir}")
    print(f"时间戳: {timestamp}")
    print(f"模式: {'预览' if dry_run else '执行'}")
    print()
    
    # 创建包目录
    if not dry_run:
        os.makedirs(package_dir, exist_ok=True)
    
    # 核心文件清单
    core_files = {
        "./基础设定/SOUL.md": "hermes-core/SOUL.md",
        "./基础设定/IDENTITY.md": "hermes-core/IDENTITY.md",
        "./USER.md": "hermes-core/USER.md",
        "./MEMORY.md": "hermes-core/MEMORY.md",
        "./基础设定/TOOLS.md": "experience/TOOLS.md",
    }
    
    # 复制核心文件
    print("📦 打包核心灵魂文件...")
    copied_files = []
    for src, dst in core_files.items():
        full_dst = os.path.join(package_dir, dst)
        if os.path.exists(src):
            if copy_file(src, full_dst, dry_run):
                copied_files.append(dst)
        else:
            print(f"⚠️  文件不存在，跳过: {src}")
    
    # 复制INSTRUCTION.md
    print("\n📦 打包启动指南...")
    instruction_src = "./skills/hermes-migration/00-INSTRUCTION.md"
    instruction_dst = os.path.join(package_dir, "00-INSTRUCTION.md")
    if os.path.exists(instruction_src):
        copy_file(instruction_src, instruction_dst, dry_run)
        copied_files.append("00-INSTRUCTION.md")
    else:
        # 如果找不到，创建简化版
        print("⚠️  00-INSTRUCTION.md 不存在，将创建简化版")
    
    # 获取并复制项目文件夹
    print("\n📦 打包项目快照...")
    projects = get_projects_list()
    projects_copied = []
    for project_path in projects:
        project_name = os.path.basename(project_path)
        dst_path = os.path.join(package_dir, "projects", project_name)
        
        if dry_run:
            print(f"[DRY-RUN] 将复制项目: {project_path} -> {dst_path}")
        else:
            try:
                # 使用shutil.copytree，排除敏感文件
                shutil.copytree(
                    project_path, 
                    dst_path,
                    ignore=shutil.ignore_patterns(
                        "*.pyc", "__pycache__", ".git", 
                        "node_modules", "*.log",
                        "SECRET*", "secret*", ".env"
                    )
                )
                print(f"✅ 已复制项目: {project_name}")
                projects_copied.append(project_name)
            except Exception as e:
                print(f"❌ 复制项目失败 {project_name}: {e}")
    
    # 创建manifest.json
    print("\n📦 生成manifest.json...")
    manifest = create_manifest(timestamp, copied_files, projects_copied or projects)
    manifest_path = os.path.join(package_dir, "manifest.json")
    
    if not dry_run:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"✅ 已生成: manifest.json")
    else:
        print(f"[DRY-RUN] 将生成: manifest.json")
    
    # 创建skill-manifest.json（双轨制）
    print("\n📦 生成skill-manifest.json（双轨制技能清单）...")
    skill_manifest = create_skill_manifest()
    skill_manifest_path = os.path.join(package_dir, "skill-manifest.json")
    
    if not dry_run:
        with open(skill_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(skill_manifest, f, ensure_ascii=False, indent=2)
        print(f"✅ 已生成: skill-manifest.json")
        print(f"   包含 {len(skill_manifest['skills'])} 个技能")
    else:
        print(f"[DRY-RUN] 将生成: skill-manifest.json")
    
    # 打包为zip
    if not dry_run:
        print("\n📦 打包为zip文件...")
        zip_path = os.path.join(output_dir, package_name)
        try:
            shutil.make_archive(zip_path, 'zip', package_dir)
            print(f"✅ 已生成zip: {zip_path}.zip")
            
            # 清理临时目录
            shutil.rmtree(package_dir)
            print(f"✅ 已清理临时目录")
            
            final_package = f"{zip_path}.zip"
        except Exception as e:
            print(f"❌ 打包失败: {e}")
            final_package = package_dir
    else:
        final_package = f"{package_dir}.zip [DRY-RUN]"
    
    # 输出总结
    print(f"\n{'='*60}")
    print("导出完成!")
    print(f"{'='*60}")
    print(f"包名: {package_name}.zip")
    print(f"路径: {final_package}")
    print(f"包含文件数: {len(copied_files)}")
    print(f"包含项目数: {len(projects_copied or projects)}")
    print()
    print("使用说明:")
    print("1. 下载此zip文件")
    print("2. 上传到新平台（MiMo Claw等）")
    print("3. 让新平台的Agent读取00-INSTRUCTION.md")
    print("4. 5分钟内Hermes将在新平台恢复")
    print()
    print("⚠️  注意: SECRET.md未包含在此包中，需在新平台重新配置")
    print(f"{'='*60}")
    
    return final_package

def main():
    parser = argparse.ArgumentParser(description="导出Hermes迁移包")
    parser.add_argument(
        "--output-dir", 
        default="./hermes-export",
        help="输出目录 (默认: ./hermes-export)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际执行"
    )
    
    args = parser.parse_args()
    
    # 创建输出目录
    if not args.dry_run:
        os.makedirs(args.output_dir, exist_ok=True)
    
    # 执行导出
    result = export_hermes(args.output_dir, args.dry_run)
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())

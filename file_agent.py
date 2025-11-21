import os
import json
import argparse
import requests
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv()

class FileStructureAgent:
    def __init__(self):
        """
        初始化Agent，从环境变量读取API密钥
        """
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("❌ 未找到DEEPSEEK_API_KEY环境变量，请检查.env文件")

    def get_folder_structure(self, folder_path):
        """
        获取文件夹的完整结构
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"路径不存在: {folder_path}")
        
        structure = {
            "name": os.path.basename(os.path.abspath(folder_path)),
            "type": "folder",
            "path": os.path.abspath(folder_path),
            "children": []
        }
        
        try:
            items = os.listdir(folder_path)
            
            for item in sorted(items):
                item_path = os.path.join(folder_path, item)
                
                if os.path.isdir(item_path):
                    structure["children"].append(self.get_folder_structure(item_path))
                else:
                    structure["children"].append({
                        "name": item,
                        "type": "file",
                        "path": item_path,
                        "size": os.path.getsize(item_path)
                    })
                    
        except PermissionError:
            print(f"⚠️ 没有权限访问: {folder_path}")
        except Exception as e:
            print(f"❌ 扫描出错: {e}")
            
        return structure

    def display_structure_tree(self, folder_path, show_size=False):
        """
        以树状格式显示文件结构
        """
        print(f"🌳 文件夹结构: {os.path.abspath(folder_path)}")
        print("=" * 70)
        self._print_tree(folder_path, "", show_size)
        print("=" * 70)

    def _print_tree(self, path, prefix, show_size=False):
        """
        递归打印树状结构
        """
        try:
            items = sorted(os.listdir(path))
            
            folders = [item for item in items if os.path.isdir(os.path.join(path, item))]
            files = [item for item in items if os.path.isfile(os.path.join(path, item))]
            
            all_items = folders + files
            total_count = len(all_items)
            
            for i, item in enumerate(all_items):
                item_path = os.path.join(path, item)
                is_last = (i == total_count - 1)
                
                if item in folders:
                    print(f"{prefix}{'└── ' if is_last else '├── '}📁 {item}/")
                    new_prefix = prefix + ('    ' if is_last else '│   ')
                    self._print_tree(item_path, new_prefix, show_size)
                else:
                    size_info = ""
                    if show_size:
                        file_size = os.path.getsize(item_path)
                        size_info = f" ({self._format_size(file_size)})"
                    print(f"{prefix}{'└── ' if is_last else '├── '}📄 {item}{size_info}")
                    
        except PermissionError:
            print(f"{prefix}└── 🔒 [权限拒绝]")
        except Exception as e:
            print(f"{prefix}└── ❌ [错误: {e}]")

    def _format_size(self, size_bytes):
        """
        格式化文件大小
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
            
        return f"{size_bytes:.1f} {size_names[i]}"

    def save_structure_to_json(self, structure, output_file):
        """
        将文件结构保存为JSON文件
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structure, f, indent=2, ensure_ascii=False)
            print(f"✅ 文件结构已保存到: {output_file}")
            return True
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return False

    def analyze_with_ai(self, folder_path, question, max_depth=3):
        """
        使用DeepSeek API分析文件结构
        """
        print("🤖 正在使用AI分析文件结构...")
        
        structure = self.get_folder_structure(folder_path)
        structure_text = self._structure_to_text(structure, max_depth=max_depth)
        
        prompt = f"""
请分析以下文件结构：

文件夹路径: {folder_path}

文件结构:
{structure_text}

问题: {question}

请根据文件结构提供详细的分析和回答。
"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个专业的文件结构分析助手。请根据用户提供的文件结构信息，分析项目类型、结构特点，并回答用户的问题。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            
            return answer
            
        except requests.exceptions.RequestException as e:
            return f"❌ API调用失败: {e}"
        except Exception as e:
            return f"❌ 处理响应时出错: {e}"

    def _structure_to_text(self, structure, level=0, max_depth=3):
        """
        将结构字典转换为可读的文本
        """
        if level > max_depth:
            return "  " * level + "...\n"
            
        text = ""
        indent = "  " * level
        
        if structure["type"] == "folder":
            text += f"{indent}📁 {structure['name']}/\n"
            for child in structure["children"]:
                text += self._structure_to_text(child, level + 1, max_depth)
        else:
            text += f"{indent}📄 {structure['name']} ({self._format_size(structure['size'])})\n"
            
        return text

    def get_structure_summary(self, folder_path):
        """
        获取文件结构统计信息
        """
        structure = self.get_folder_structure(folder_path)
        
        def count_items(struct):
            folders = 0
            files = 0
            total_size = 0
            
            if struct["type"] == "folder":
                folders += 1
                for child in struct["children"]:
                    if child["type"] == "folder":
                        sub_folders, sub_files, sub_size = count_items(child)
                        folders += sub_folders
                        files += sub_files
                        total_size += sub_size
                    else:
                        files += 1
                        total_size += child.get("size", 0)
            
            return folders, files, total_size
        
        folders, files, total_size = count_items(structure)
        
        summary = f"""
📊 文件结构统计:
├── 📁 文件夹数量: {folders}
├── 📄 文件数量: {files}
├── 💾 总大小: {self._format_size(total_size)}
└── 📍 扫描路径: {folder_path}
"""
        return summary

def setup_argument_parser():
    """
    设置命令行参数解析器
    """
    parser = argparse.ArgumentParser(
        description="🚀 DeepSeek 文件结构分析Agent - 读取本地文件夹结构并使用AI分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 显示当前目录的树状结构
  python cli_file_agent.py --tree
  
  # 显示指定目录的树状结构并显示文件大小
  python cli_file_agent.py --tree --path /path/to/folder --size
  
  # 保存文件结构到JSON
  python cli_file_agent.py --json output.json --path /path/to/folder
  
  # 使用AI分析文件结构
  python cli_file_agent.py --ai "这个项目是做什么的?" --path /path/to/folder
  
  # 显示统计信息
  python cli_file_agent.py --stats
  
  # 执行所有操作
  python cli_file_agent.py --all
        """
    )
    
    # 主要参数组
    parser.add_argument(
        "--path", "-p",
        type=str,
        default=".",
        help="要扫描的文件夹路径 (默认: 当前目录)"
    )
    
    # 功能参数组
    parser.add_argument(
        "--tree", "-t",
        action="store_true",
        help="显示文件树状结构"
    )
    
    parser.add_argument(
        "--size", "-s",
        action="store_true",
        help="在树状结构中显示文件大小"
    )
    
    parser.add_argument(
        "--json", "-j",
        type=str,
        metavar="FILE",
        help="保存文件结构到指定的JSON文件"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示文件结构统计信息"
    )
    
    parser.add_argument(
        "--ai",
        type=str,
        metavar="QUESTION",
        help="使用AI分析文件结构并回答问题"
    )
    
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="AI分析时的最大目录深度 (默认: 3)"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="执行所有操作: 显示树状结构、统计信息、保存JSON、AI分析"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="file_structure.json",
        help="JSON输出文件名 (默认: file_structure.json)"
    )
    
    return parser

def main():
    """
    主函数 - 命令行接口
    """
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    try:
        # 创建Agent实例
        agent = FileStructureAgent()
        print("🚀 DeepSeek 文件结构分析Agent")
        print(f"📍 扫描路径: {os.path.abspath(args.path)}")
        print("-" * 50)
        
        # 检查路径是否存在
        if not os.path.exists(args.path):
            print(f"❌ 错误: 路径不存在 '{args.path}'")
            return 1
        
        # 执行所有操作
        if args.all:
            print("\n📋 执行所有操作...")
            args.tree = True
            args.stats = True
            args.json = args.output
            args.ai = "请分析这个项目的结构、类型和可能的用途"
        
        results = {}
        
        # 显示树状结构
        if args.tree:
            print("\n🌳 文件结构树:")
            agent.display_structure_tree(args.path, args.size)
            results['tree'] = True
        
        # 显示统计信息
        if args.stats:
            print("\n📊 统计信息:")
            summary = agent.get_structure_summary(args.path)
            print(summary)
            results['stats'] = True
        
        # 保存到JSON
        if args.json:
            print(f"\n💾 保存文件结构到: {args.json}")
            structure = agent.get_folder_structure(args.path)
            if agent.save_structure_to_json(structure, args.json):
                results['json'] = args.json
        
        # AI分析
        if args.ai:
            print(f"\n🤖 AI分析:")
            print(f"问题: {args.ai}")
            print("-" * 50)
            answer = agent.analyze_with_ai(args.path, args.ai, args.depth)
            print(answer)
            print("-" * 50)
            results['ai'] = True
        
        # 如果没有指定任何操作，显示帮助
        if not any([args.tree, args.stats, args.json, args.ai, args.all]):
            parser.print_help()
            print(f"\n💡 提示: 使用 --all 执行所有操作")
        
        # 显示执行结果摘要
        if results:
            print(f"\n✅ 操作完成!")
            for operation, result in results.items():
                if operation == 'json':
                    print(f"   📁 JSON文件: {result}")
                else:
                    print(f"   ✅ {operation.upper()}: 完成")
        
        return 0
        
    except ValueError as e:
        print(f"❌ {e}")
        print("\n💡 解决方案:")
        print("1. 创建 .env 文件并在其中添加:")
        print("   DEEPSEEK_API_KEY=你的deepseek_api密钥")
        print("2. 重新运行程序")
        return 1
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
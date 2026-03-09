# Python CLI 项目最佳实践

本文档总结了在开发 HEIC to JPG Converter 项目过程中应用的 Python 最佳实践。

## 项目配置

### pyproject.toml 现代化配置

使用 `pyproject.toml` 作为唯一的配置文件，遵循 PEP 621 标准：

```toml
[project]
name = "pic-format-converter"
version = "0.1.0"
description = "Convert HEIC/HEIF images to JPG format"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "pillow>=10.0.0",
    "pillow-heif>=0.18.0",
    "typer>=0.12.0",
    "rich>=13.0.0",
]

[project.scripts]
heic2jpg = "main:app"

[tool.uv]
package = true
```

**关键点**：
- 使用 `requires-python` 明确 Python 版本要求
- 依赖版本使用 `>=` 约束，保持灵活性
- `[project.scripts]` 定义命令行入口点
- `[tool.uv]` 配置包管理器选项

### .python-version 文件

放置 `.python-version` 文件指定 Python 版本，兼容 pyenv、uv 等工具：

```
3.14
```

## 依赖选择原则

### 图像处理库选型

| 需求 | 选择 | 理由 |
|------|------|------|
| HEIC 解码 | `pillow-heif` | 官方推荐插件，维护活跃，EXIF 支持完善 |
| 图像处理 | `Pillow` | Python 标准库，生态成熟 |
| CLI 框架 | `typer` | 类型安全，自动生成帮助，基于 click |
| 终端美化 | `rich` | 进度条、彩色输出，typer 内置支持 |

### 依赖版本策略

- **主依赖**: 使用 `>=` 约束，允许小版本更新
- **避免锁定**: 不提交 `uv.lock` 到版本控制（除非是应用而非库）
- **最小依赖**: 只添加必要的依赖，减少攻击面

## CLI 设计模式

### Typer 最佳实践

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="heic2jpg",
    help="Convert HEIC/HEIF images to JPG format",
    add_completion=False,  # 禁用 shell 补全安装提示
)
console = Console()


@app.command()
def main(
    inputs: list[Path] = typer.Argument(
        ...,
        help="Input HEIC file(s) or directory(s) to convert",
    ),
    quality: int = typer.Option(
        90,
        "-q", "--quality",
        min=1,
        max=100,
        help="JPG quality (1-100, default: 90)",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing output files",
    ),
) -> None:
    """Convert HEIC/HEIF images to JPG format."""
    # 实现逻辑
```

**设计要点**：
- 使用 `typer.Argument` 定义位置参数
- 使用 `typer.Option` 定义可选参数，同时提供短选项和长选项
- 使用 `min/max` 约束数值范围
- 布尔选项使用 `--flag` 形式，默认值设为 `False`

### 退出码处理

```python
from typer import Exit

# 错误时返回非零退出码
if error_condition:
    console.print("[red]Error message[/red]")
    raise typer.Exit(1)
```

## 并行处理模式

### 使用 ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress

def batch_convert(files: list[Path], workers: int = 4) -> None:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # 提交任务
        future_to_file = {
            executor.submit(convert_file, f): f
            for f in files
        }

        # 收集结果并显示进度
        with Progress() as progress:
            task = progress.add_task("Converting...", total=len(files))
            for future in as_completed(future_to_file):
                result = future.result()
                progress.advance(task)
```

**注意事项**：
- I/O 密集型任务使用多线程（ThreadPoolExecutor）
- CPU 密集型任务使用多进程（ProcessPoolExecutor）
- 使用 `as_completed` 实时获取完成的任务
- 合理设置 `max_workers`，通常为 CPU 核心数的 2-4 倍

## 文件路径处理

### 使用 pathlib.Path

```python
from pathlib import Path

# 推荐：使用 Path 对象
input_path = Path("photo.heic")
output_path = input_path.with_suffix(".jpg")

# 检查文件存在
if not input_path.exists():
    console.print(f"File not found: {input_path}")

# 创建目录
output_path.parent.mkdir(parents=True, exist_ok=True)

# 遍历目录
for file in directory.glob("*.heic"):
    process(file)
```

**优势**：
- 跨平台路径处理
- 链式调用，代码简洁
- 内置路径操作方法

## EXIF 处理

### 图像方向校正

HEIC 文件可能包含 EXIF Orientation 标签，需要在转换时应用：

```python
from PIL import Image, ExifTags

def apply_orientation(img: Image.Image) -> Image.Image:
    try:
        exif = img.getexif()
        orientation_key = next(
            k for k, v in ExifTags.TAGS.items() if v == "Orientation"
        )
        orientation = exif.get(orientation_key, 1)

        if orientation == 3:
            img = img.rotate(180, expand=True)
        elif orientation == 6:
            img = img.rotate(-90, expand=True)
        elif orientation == 8:
            img = img.rotate(90, expand=True)
        # ... 其他方向处理

        return img
    except Exception:
        return img
```

### 保留 EXIF 数据

```python
# 获取 EXIF 数据
exif_data = img.info.get("exif")

# 保存时传递 EXIF
img.save(output_path, "JPEG", quality=quality, exif=exif_data)
```

## 错误处理策略

### 函数返回值模式

```python
def convert_file(path: Path) -> tuple[bool, str]:
    """返回 (成功状态, 消息) 元组"""
    try:
        # 转换逻辑
        return True, f"Converted: {path.name}"
    except FileNotFoundError:
        return False, f"File not found: {path}"
    except PermissionError:
        return False, f"Permission denied: {path}"
    except Exception as e:
        return False, f"Unexpected error: {e}"
```

### 资源管理

```python
def convert_file(path: Path) -> bool:
    img = Image.open(path)
    try:
        # 处理图像
        img.save(output_path, "JPEG")
        return True
    finally:
        img.close()  # 确保资源释放
```

## 代码风格

### 类型注解

Python 3.14 支持现代类型注解语法：

```python
from __future__ import annotations

def process_files(
    inputs: list[Path],
    output_dir: Path | None = None,
) -> dict[str, int]:
    """处理文件并返回统计结果"""
    ...
```

### 文档字符串

```python
def convert_heic_to_jpg(
    input_path: Path,
    output_path: Path,
    quality: int = 90,
) -> tuple[bool, str]:
    """
    将 HEIC 文件转换为 JPG 格式。

    Args:
        input_path: 输入 HEIC 文件路径
        output_path: 输出 JPG 文件路径
        quality: JPG 质量 (1-100)

    Returns:
        元组 (成功状态, 消息)
    """
```

## 项目结构

单文件 CLI 项目的推荐结构：

```
project/
├── main.py              # CLI 入口点和核心逻辑
├── pyproject.toml       # 项目配置和依赖
├── README.md            # 使用文档
├── BEST_PRACTICES.md    # 最佳实践文档
└── .python-version      # Python 版本
```

复杂项目可扩展为：

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── cli.py       # CLI 入口
│       ├── core.py      # 核心逻辑
│       └── utils.py     # 工具函数
├── tests/
├── pyproject.toml
└── README.md
```

## 开发工作流

### 安装和运行

```bash
# 安装依赖
uv sync

# 运行 CLI
uv run heic2jpg --help

# 开发模式安装
uv pip install -e .
```

### 依赖管理

```bash
# 添加依赖
uv add pillow typer

# 添加开发依赖
uv add --dev pytest ruff

# 更新依赖
uv lock --upgrade
```

## 注意事项清单

- [ ] 使用 `pathlib.Path` 处理文件路径
- [ ] 使用 `try/finally` 或 `with` 语句管理资源
- [ ] 函数返回明确的成功/失败状态
- [ ] CLI 参数提供 `-h/--help` 帮助信息
- [ ] 使用彩色输出区分成功/错误信息
- [ ] 批量操作显示进度条
- [ ] 处理 EXIF 方向和元数据保留
- [ ] 设置合理的默认值和参数约束
- [ ] 提供清晰的用户文档和示例
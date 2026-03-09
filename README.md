配置：vscode + claude code + 百炼GLM5

指令：
> 1. 使用 Python3.14 创建一个 CLI 程序，实现将 HEIC 文件转换为 JPG 文件
> 2. 将当前项目的设计思路中符合 Python 最佳实践的内容提炼成一个新的 md 文档（readme），供 Python 初学者学习使用，文件放在根目录中。
> 3. 在项目根目录增加 `.gitignore` 文件，避免当前项目中不必要或机密内容上传至 github 泄露


以下均为 AI 生成。
---
# HEIC to JPG Converter

将 HEIC/HEIF 图像文件转换为 JPG 格式的命令行工具。

## 安装

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

## 使用方法

### 基本用法

```bash
# 转换单个文件 (输出为同名 .jpg 文件)
heic2jpg photo.heic

# 指定输出文件名
heic2jpg photo.heic -o output.jpg

# 转换到指定目录
heic2jpg photo.heic -d converted/
```

### 批量转换

```bash
# 转换当前目录所有 HEIC 文件
heic2jpg *.heic

# 转换指定目录下的所有 HEIC 文件
heic2jpg photos/

# 转换到指定目录
heic2jpg *.heic -d output/

# 并行转换 (加速批量处理)
heic2jpg *.heic --workers 8
```

### 质量设置

```bash
# 设置 JPG 质量 (1-100, 默认 90)
heic2jpg photo.heic -q 95
```

### 其他选项

```bash
# 保留 EXIF 元数据 (默认开启)
heic2jpg photo.heic --preserve-exif

# 不保留 EXIF 元数据
heic2jpg photo.heic --no-preserve-exif

# 覆盖已存在的文件
heic2jpg photo.heic --overwrite
```

## 帮助信息

```bash
heic2jpg --help
```

## 功能特性

- 支持单文件和批量转换
- 自动处理 EXIF 方向信息
- 保留 EXIF 元数据 (相机型号、拍摄时间、GPS 等)
- 并行处理加速批量转换
- 进度条显示
- 彩色终端输出

## 注意事项

1. **EXIF 方向**: HEIC 文件可能包含方向元数据，转换时会自动应用旋转
2. **颜色配置**: 保留原始颜色配置文件
3. **Alpha 通道**: JPG 不支持透明，RGBA 图像会自动转换为 RGB
4. **文件大小**: HEIC 压缩效率通常高于 JPG，转换后文件可能变大

## 依赖

- Python >= 3.14
- Pillow - 图像处理
- pillow-heif - HEIC 格式支持
- Typer - CLI 框架
- Rich - 终端美化输出

## 许可证

MIT License
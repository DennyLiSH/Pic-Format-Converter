"""HEIC to JPG CLI Converter - Convert HEIC/HEIF images to JPG format."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pillow_heif
import typer
from PIL import Image, ExifTags
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Register HEIF opener
pillow_heif.register_heif_opener()

app = typer.Typer(
    name="heic2jpg",
    help="Convert HEIC/HEIF images to JPG format",
    add_completion=False,
)
console = Console()


def apply_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation tag to image and return corrected image."""
    try:
        exif = img.getexif()
        if not exif:
            return img

        # Find orientation tag
        orientation_key = None
        for key, val in ExifTags.TAGS.items():
            if val == "Orientation":
                orientation_key = key
                break

        if orientation_key is None:
            return img

        orientation = exif.get(orientation_key)
        if orientation is None:
            return img

        # Apply orientation transformations
        if orientation == 2:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            img = img.rotate(180, expand=True)
        elif orientation == 4:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            img = img.rotate(-90, expand=True).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 6:
            img = img.rotate(-90, expand=True)
        elif orientation == 7:
            img = img.rotate(90, expand=True).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 8:
            img = img.rotate(90, expand=True)

        return img
    except Exception:
        return img


def convert_heic_to_jpg(
    input_path: Path,
    output_path: Path,
    quality: int = 90,
    preserve_exif: bool = True,
    overwrite: bool = False,
) -> tuple[bool, str]:
    """
    Convert a single HEIC file to JPG.

    Returns:
        tuple of (success: bool, message: str)
    """
    # Check if output exists
    if output_path.exists() and not overwrite:
        return False, f"Output file already exists: {output_path}"

    # Open HEIC file
    try:
        img = Image.open(input_path)
    except Exception as e:
        return False, f"Failed to open {input_path}: {e}"

    try:
        # Apply orientation from EXIF
        img = apply_orientation(img)

        # Convert to RGB (JPG doesn't support alpha channel)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Get EXIF data
        exif_data = None
        if preserve_exif:
            try:
                exif_data = img.info.get("exif")
            except Exception:
                pass

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as JPG
        img.save(
            output_path,
            "JPEG",
            quality=quality,
            exif=exif_data,
        )

        return True, f"Converted: {input_path.name} -> {output_path.name}"
    except Exception as e:
        return False, f"Failed to convert {input_path}: {e}"
    finally:
        img.close()


def get_output_path(
    input_path: Path,
    output_dir: Path | None,
    output_file: Path | None = None,
) -> Path:
    """Determine the output path for a converted file."""
    if output_file:
        return output_file

    stem = input_path.stem
    if output_dir:
        return output_dir / f"{stem}.jpg"
    else:
        return input_path.parent / f"{stem}.jpg"


def collect_heic_files(inputs: list[Path]) -> list[Path]:
    """Collect all HEIC files from input paths (supports directories and glob patterns)."""
    files = []
    heic_extensions = {".heic", ".heif"}

    for path in inputs:
        if path.is_file():
            if path.suffix.lower() in heic_extensions:
                files.append(path)
        elif path.is_dir():
            for ext in heic_extensions:
                files.extend(path.glob(f"*{ext}"))
                files.extend(path.glob(f"*{ext.upper()}"))

    return sorted(set(files))


@app.command()
def main(
    inputs: list[Path] = typer.Argument(
        ...,
        help="Input HEIC file(s) or directory(s) to convert",
        exists=False,  # We handle this manually for better error messages
    ),
    output: Path | None = typer.Option(
        None,
        "-o", "--output",
        help="Output file name (only for single file conversion)",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "-d", "--dir",
        help="Output directory for converted files",
    ),
    quality: int = typer.Option(
        90,
        "-q", "--quality",
        min=1,
        max=100,
        help="JPG quality (1-100, default: 90)",
    ),
    preserve_exif: bool = typer.Option(
        True,
        "--preserve-exif/--no-preserve-exif",
        help="Preserve EXIF metadata (default: preserve)",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing output files",
    ),
    workers: int = typer.Option(
        4,
        "-w", "--workers",
        min=1,
        max=32,
        help="Number of parallel workers for batch conversion (default: 4)",
    ),
) -> None:
    """
    Convert HEIC/HEIF images to JPG format.

    Examples:

        # Convert a single file
        heic2jpg photo.heic

        # Convert with custom output name
        heic2jpg photo.heic -o output.jpg

        # Convert multiple files
        heic2jpg *.heic

        # Convert with custom quality
        heic2jpg photo.heic -q 95

        # Convert to a specific directory
        heic2jpg *.heic -d converted/

        # Parallel batch conversion
        heic2jpg *.heic --workers 8
    """
    # Validate input paths
    valid_inputs = []
    for path in inputs:
        if path.exists():
            valid_inputs.append(path)
        else:
            console.print(f"[red]Error: Path not found: {path}[/red]")

    if not valid_inputs:
        console.print("[red]Error: No valid input files found[/red]")
        raise typer.Exit(1)

    # Collect HEIC files
    heic_files = collect_heic_files(valid_inputs)

    if not heic_files:
        console.print("[red]Error: No HEIC/HEIF files found in the specified paths[/red]")
        raise typer.Exit(1)

    # Single file conversion
    if len(heic_files) == 1:
        input_path = heic_files[0]
        output_path = get_output_path(input_path, output_dir, output)

        console.print(f"[blue]Converting[/blue] {input_path.name}...")
        success, message = convert_heic_to_jpg(
            input_path,
            output_path,
            quality,
            preserve_exif,
            overwrite,
        )

        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]✗[/red] {message}")
            raise typer.Exit(1)

        return

    # Batch conversion with progress bar
    console.print(f"[blue]Converting {len(heic_files)} files...[/blue]")

    # Create output directory if specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Parallel conversion
    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Converting...", total=len(heic_files))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(
                    convert_heic_to_jpg,
                    file_path,
                    get_output_path(file_path, output_dir),
                    quality,
                    preserve_exif,
                    overwrite,
                ): file_path
                for file_path in heic_files
            }

            for future in as_completed(future_to_file):
                success, message = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    console.print(f"[red]✗[/red] {message}")

                progress.advance(task)

    # Summary
    console.print()
    console.print(f"[green]Successfully converted: {success_count}[/green]")
    if fail_count > 0:
        console.print(f"[red]Failed: {fail_count}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
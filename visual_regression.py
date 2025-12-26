#!/usr/bin/env python3
"""
Visual Regression Testing Module
Provides pixel-perfect visual comparison between screenshots.
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageChops, ImageDraw, ImageFont
import json


class VisualRegressionTester:
    """Handles visual regression testing with baseline comparison."""

    def __init__(self, project_dir: Path):
        """
        Initialize visual regression tester.

        Args:
            project_dir: Path to project directory for storing baselines
        """
        self.project_dir = Path(project_dir)
        self.baselines_dir = self.project_dir / "baselines"
        self.baselines_dir.mkdir(parents=True, exist_ok=True)
        self.diffs_dir = self.project_dir / "diffs"
        self.diffs_dir.mkdir(parents=True, exist_ok=True)

    def get_baseline_path(self, name: str) -> Path:
        """Get path for baseline screenshot."""
        # Create safe filename from name
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)
        return self.baselines_dir / f"{safe_name}.png"

    def get_diff_path(self, name: str) -> Path:
        """Get path for diff screenshot."""
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)
        return self.diffs_dir / f"{safe_name}_diff.png"

    def set_baseline(self, name: str, screenshot_path: Path) -> bool:
        """
        Set a screenshot as the baseline for future comparisons.

        Args:
            name: Name/identifier for this baseline
            screenshot_path: Path to the screenshot to use as baseline

        Returns:
            True if baseline was set successfully
        """
        try:
            baseline_path = self.get_baseline_path(name)

            # Copy screenshot to baselines directory
            img = Image.open(screenshot_path)
            img.save(baseline_path, 'PNG')

            # Store metadata
            metadata = {
                'name': name,
                'original_path': str(screenshot_path),
                'created_at': str(Path(screenshot_path).stat().st_mtime),
                'size': {'width': img.width, 'height': img.height}
            }

            metadata_path = baseline_path.with_suffix('.json')
            metadata_path.write_text(json.dumps(metadata, indent=2))

            return True
        except Exception as e:
            print(f"Error setting baseline: {e}")
            return False

    def compare(
        self,
        name: str,
        current_screenshot: Path,
        threshold: float = 0.1
    ) -> Dict:
        """
        Compare current screenshot against baseline.

        Args:
            name: Name of the baseline to compare against
            current_screenshot: Path to current screenshot
            threshold: Difference threshold (0.0-1.0), lower is more strict

        Returns:
            Dictionary with comparison results:
            - matched: bool, whether images match within threshold
            - diff_percentage: float, percentage of pixels that differ
            - diff_image_path: str, path to diff image if different
            - baseline_exists: bool, whether baseline exists
        """
        baseline_path = self.get_baseline_path(name)

        result = {
            'name': name,
            'baseline_exists': baseline_path.exists(),
            'matched': False,
            'diff_percentage': 0.0,
            'diff_image_path': None,
            'threshold': threshold
        }

        if not baseline_path.exists():
            result['message'] = 'No baseline exists. Set baseline first.'
            return result

        try:
            # Load images
            baseline = Image.open(baseline_path).convert('RGB')
            current = Image.open(current_screenshot).convert('RGB')

            # Check if dimensions match
            if baseline.size != current.size:
                # Resize current to match baseline for comparison
                current = current.resize(baseline.size, Image.LANCZOS)
                result['resized'] = True

            # Calculate pixel differences
            diff = ImageChops.difference(baseline, current)

            # Calculate diff percentage
            pixels = list(diff.getdata())
            total_pixels = len(pixels)
            diff_pixels = sum(1 for pixel in pixels if sum(pixel) > 30)  # Threshold for "different"
            diff_percentage = (diff_pixels / total_pixels) * 100

            result['diff_percentage'] = diff_percentage
            result['matched'] = diff_percentage <= (threshold * 100)

            # Create visual diff if different
            if not result['matched']:
                diff_image = self._create_diff_image(baseline, current, diff)
                diff_path = self.get_diff_path(name)
                diff_image.save(diff_path, 'PNG')
                result['diff_image_path'] = str(diff_path)

            return result

        except Exception as e:
            result['error'] = str(e)
            return result

    def _create_diff_image(
        self,
        baseline: Image.Image,
        current: Image.Image,
        diff: Image.Image
    ) -> Image.Image:
        """
        Create a visual diff image showing baseline, current, and differences.

        Args:
            baseline: Baseline image
            current: Current image
            diff: Difference image

        Returns:
            Combined diff image
        """
        # Create side-by-side comparison
        width = baseline.width
        height = baseline.height

        # Create new image with 3 panels
        combined = Image.new('RGB', (width * 3, height + 40), (255, 255, 255))

        # Add labels
        draw = ImageDraw.Draw(combined)
        try:
            # Try to use a better font, fall back to default if not available
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()

        # Paste images
        combined.paste(baseline, (0, 40))
        combined.paste(current, (width, 40))

        # Highlight differences in red
        diff_highlight = diff.convert('RGB')
        diff_pixels = diff_highlight.load()
        for y in range(diff_highlight.height):
            for x in range(diff_highlight.width):
                r, g, b = diff_pixels[x, y]
                if r + g + b > 30:  # If pixel is different
                    diff_pixels[x, y] = (255, 0, 0)  # Make it red
                else:
                    diff_pixels[x, y] = (0, 0, 0)  # Make it black

        combined.paste(diff_highlight, (width * 2, 40))

        # Add labels
        draw.text((width // 2 - 40, 10), "Baseline", fill=(0, 0, 0), font=font)
        draw.text((width + width // 2 - 40, 10), "Current", fill=(0, 0, 0), font=font)
        draw.text((width * 2 + width // 2 - 40, 10), "Diff (Red)", fill=(255, 0, 0), font=font)

        return combined

    def get_baselines(self) -> List[Dict]:
        """
        Get list of all available baselines.

        Returns:
            List of baseline metadata dictionaries
        """
        baselines = []

        for baseline_file in self.baselines_dir.glob("*.png"):
            metadata_file = baseline_file.with_suffix('.json')

            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                    metadata['path'] = str(baseline_file)
                    baselines.append(metadata)
                except:
                    pass

        return baselines

    def delete_baseline(self, name: str) -> bool:
        """
        Delete a baseline.

        Args:
            name: Name of baseline to delete

        Returns:
            True if deleted successfully
        """
        try:
            baseline_path = self.get_baseline_path(name)
            metadata_path = baseline_path.with_suffix('.json')

            if baseline_path.exists():
                baseline_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

            return True
        except Exception as e:
            print(f"Error deleting baseline: {e}")
            return False


# Example usage
if __name__ == "__main__":
    import tempfile

    # Create test project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        vrt = VisualRegressionTester(Path(tmpdir))

        # Create test image
        test_img = Image.new('RGB', (800, 600), color='white')
        test_path = Path(tmpdir) / "test.png"
        test_img.save(test_path)

        # Set baseline
        vrt.set_baseline("homepage", test_path)

        # Compare with slight difference
        test_img2 = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(test_img2)
        draw.rectangle([100, 100, 200, 200], fill='red')
        test_path2 = Path(tmpdir) / "test2.png"
        test_img2.save(test_path2)

        result = vrt.compare("homepage", test_path2, threshold=0.05)
        print(json.dumps(result, indent=2))

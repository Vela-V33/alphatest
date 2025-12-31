#!/usr/bin/env python3
"""
AlphaTest - Screenshot Generator Module
Generates marketing-ready screenshots with device frames
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile


class DeviceFrame:
    """Device frame specifications and templates"""

    FRAMES = {
        'macbook': {
            'name': 'MacBook Pro',
            'width': 3024,
            'height': 1964,
            'screen_x': 302,
            'screen_y': 190,
            'screen_width': 2420,
            'screen_height': 1512,
            'scale': 2,  # Retina
            'color': 'space-gray'
        },
        'iphone': {
            'name': 'iPhone 15 Pro',
            'width': 1290,
            'height': 2796,
            'screen_x': 60,
            'screen_y': 160,
            'screen_width': 1170,
            'screen_height': 2476,
            'scale': 3,  # Super Retina
            'has_dynamic_island': True
        },
        'android': {
            'name': 'Pixel 8 Pro',
            'width': 1344,
            'height': 2992,
            'screen_x': 40,
            'screen_y': 140,
            'screen_width': 1264,
            'screen_height': 2712,
            'scale': 3
        },
        'ipad': {
            'name': 'iPad Pro 12.9"',
            'width': 2732,
            'height': 2048,
            'screen_x': 80,
            'screen_y': 80,
            'screen_width': 2572,
            'screen_height': 1888,
            'scale': 2
        },
        'desktop': {
            'name': 'Desktop Browser',
            'width': 1920,
            'height': 1080,
            'screen_x': 0,
            'screen_y': 80,  # Browser chrome height
            'screen_width': 1920,
            'screen_height': 1000,
            'scale': 1,
            'has_browser_chrome': True
        }
    }

    @staticmethod
    def get_frame_spec(device_type: str) -> Dict:
        """Get device frame specifications"""
        return DeviceFrame.FRAMES.get(device_type, DeviceFrame.FRAMES['desktop'])


class ScreenshotGenerator:
    """Generate marketing screenshots with device frames"""

    def __init__(self, project_id: str, output_dir: str = None):
        self.project_id = project_id
        self.output_dir = output_dir or f"screenshots/{project_id}"
        self.screenshots = []

        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def capture_screenshot(self, page, url: str, description: str = None) -> bytes:
        """Capture screenshot from Playwright page"""
        return page.screenshot(full_page=True, type='png')

    def apply_device_frame(self, screenshot_bytes: bytes, device_type: str) -> Tuple[Image.Image, Dict]:
        """Apply device frame overlay to screenshot"""
        spec = DeviceFrame.get_frame_spec(device_type)

        # Load screenshot
        screenshot = Image.open(io.BytesIO(screenshot_bytes))

        # Resize screenshot to fit device screen
        screen_size = (spec['screen_width'], spec['screen_height'])
        screenshot_resized = screenshot.resize(screen_size, Image.Resampling.LANCZOS)

        # Create device frame
        frame = self._create_device_frame(device_type, spec)

        # Composite screenshot onto frame
        frame.paste(screenshot_resized, (spec['screen_x'], spec['screen_y']))

        return frame, spec

    def _create_device_frame(self, device_type: str, spec: Dict) -> Image.Image:
        """Create device frame with transparent background"""
        width = spec['width']
        height = spec['height']

        # Create transparent image
        frame = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)

        if device_type == 'macbook':
            return self._create_macbook_frame(frame, draw, spec)
        elif device_type == 'iphone':
            return self._create_iphone_frame(frame, draw, spec)
        elif device_type == 'android':
            return self._create_android_frame(frame, draw, spec)
        elif device_type == 'ipad':
            return self._create_ipad_frame(frame, draw, spec)
        elif device_type == 'desktop':
            return self._create_desktop_frame(frame, draw, spec)

        return frame

    def _create_macbook_frame(self, frame: Image.Image, draw: ImageDraw, spec: Dict) -> Image.Image:
        """Create MacBook Pro frame"""
        width = spec['width']
        height = spec['height']
        sx = spec['screen_x']
        sy = spec['screen_y']
        sw = spec['screen_width']
        sh = spec['screen_height']

        # Device body (rounded rectangle)
        body_color = (45, 45, 48, 255)  # Space Gray
        bezel_radius = 40

        # Draw main body with rounded corners
        draw.rounded_rectangle([(0, 0), (width, height)], radius=bezel_radius, fill=body_color)

        # Screen bezel (slightly darker)
        bezel_color = (30, 30, 32, 255)
        bezel_width = sx
        draw.rounded_rectangle(
            [(bezel_width // 2, bezel_width // 2),
             (width - bezel_width // 2, height - bezel_width // 2)],
            radius=bezel_radius - 10,
            fill=bezel_color
        )

        # Screen area (will be replaced with screenshot)
        draw.rectangle([(sx, sy), (sx + sw, sy + sh)], fill=(0, 0, 0, 255))

        # Notch (if has notch)
        notch_width = 200
        notch_height = 30
        notch_x = (width - notch_width) // 2
        draw.rounded_rectangle(
            [(notch_x, sy - 5), (notch_x + notch_width, sy + notch_height)],
            radius=15,
            fill=body_color
        )

        # Camera dot
        camera_x = width // 2
        camera_y = sy + 10
        draw.ellipse(
            [(camera_x - 5, camera_y - 5), (camera_x + 5, camera_y + 5)],
            fill=(20, 20, 22, 255)
        )

        return frame

    def _create_iphone_frame(self, frame: Image.Image, draw: ImageDraw, spec: Dict) -> Image.Image:
        """Create iPhone 15 Pro frame"""
        width = spec['width']
        height = spec['height']
        sx = spec['screen_x']
        sy = spec['screen_y']
        sw = spec['screen_width']
        sh = spec['screen_height']

        # Device body
        body_color = (40, 40, 43, 255)  # Space Black
        corner_radius = 55

        # Draw device body
        draw.rounded_rectangle([(0, 0), (width, height)], radius=corner_radius, fill=body_color)

        # Screen area
        screen_radius = 45
        draw.rounded_rectangle(
            [(sx, sy), (sx + sw, sy + sh)],
            radius=screen_radius,
            fill=(0, 0, 0, 255)
        )

        # Dynamic Island
        if spec.get('has_dynamic_island'):
            island_width = 120
            island_height = 35
            island_x = (width - island_width) // 2
            island_y = sy + 40
            draw.rounded_rectangle(
                [(island_x, island_y), (island_x + island_width, island_y + island_height)],
                radius=17,
                fill=body_color
            )

        # Side buttons (volume, power)
        button_color = (60, 60, 65, 255)
        # Volume buttons
        draw.rectangle([(10, 250), (20, 320)], fill=button_color)
        draw.rectangle([(10, 350), (20, 420)], fill=button_color)
        # Power button
        draw.rectangle([(width - 20, 300), (width - 10, 400)], fill=button_color)

        return frame

    def _create_android_frame(self, frame: Image.Image, draw: ImageDraw, spec: Dict) -> Image.Image:
        """Create Android Pixel frame"""
        width = spec['width']
        height = spec['height']
        sx = spec['screen_x']
        sy = spec['screen_y']
        sw = spec['screen_width']
        sh = spec['screen_height']

        # Device body
        body_color = (50, 50, 55, 255)  # Obsidian
        corner_radius = 50

        # Draw device body
        draw.rounded_rectangle([(0, 0), (width, height)], radius=corner_radius, fill=body_color)

        # Screen area
        screen_radius = 40
        draw.rounded_rectangle(
            [(sx, sy), (sx + sw, sy + sh)],
            radius=screen_radius,
            fill=(0, 0, 0, 255)
        )

        # Front camera (centered punch-hole)
        camera_x = width // 2
        camera_y = sy + 50
        draw.ellipse(
            [(camera_x - 15, camera_y - 15), (camera_x + 15, camera_y + 15)],
            fill=body_color
        )

        # Power button
        button_color = (70, 70, 75, 255)
        draw.rectangle([(width - 20, 280), (width - 10, 380)], fill=button_color)

        return frame

    def _create_ipad_frame(self, frame: Image.Image, draw: ImageDraw, spec: Dict) -> Image.Image:
        """Create iPad Pro frame"""
        width = spec['width']
        height = spec['height']
        sx = spec['screen_x']
        sy = spec['screen_y']
        sw = spec['screen_width']
        sh = spec['screen_height']

        # Device body
        body_color = (45, 45, 48, 255)  # Space Gray
        corner_radius = 50

        # Draw device body
        draw.rounded_rectangle([(0, 0), (width, height)], radius=corner_radius, fill=body_color)

        # Screen area
        screen_radius = 35
        draw.rounded_rectangle(
            [(sx, sy), (sx + sw, sy + sh)],
            radius=screen_radius,
            fill=(0, 0, 0, 255)
        )

        # Front camera (top center)
        camera_x = width // 2
        camera_y = 40
        draw.ellipse(
            [(camera_x - 8, camera_y - 8), (camera_x + 8, camera_y + 8)],
            fill=(20, 20, 22, 255)
        )

        return frame

    def _create_desktop_frame(self, frame: Image.Image, draw: ImageDraw, spec: Dict) -> Image.Image:
        """Create desktop browser chrome"""
        width = spec['width']
        height = spec['height']
        chrome_height = spec['screen_y']

        # Browser chrome background
        chrome_color = (240, 240, 245, 255)  # Light gray chrome
        draw.rectangle([(0, 0), (width, chrome_height)], fill=chrome_color)

        # Traffic light buttons (macOS style)
        button_y = chrome_height // 2
        button_spacing = 25
        close_x = 20

        # Close (red)
        draw.ellipse(
            [(close_x - 8, button_y - 8), (close_x + 8, button_y + 8)],
            fill=(255, 95, 86, 255)
        )
        # Minimize (yellow)
        minimize_x = close_x + button_spacing
        draw.ellipse(
            [(minimize_x - 8, button_y - 8), (minimize_x + 8, button_y + 8)],
            fill=(255, 189, 46, 255)
        )
        # Maximize (green)
        maximize_x = minimize_x + button_spacing
        draw.ellipse(
            [(maximize_x - 8, button_y - 8), (maximize_x + 8, button_y + 8)],
            fill=(40, 201, 64, 255)
        )

        # Address bar
        bar_x = 120
        bar_y = (chrome_height - 36) // 2
        bar_width = width - 240
        bar_height = 36
        draw.rounded_rectangle(
            [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
            radius=8,
            fill=(255, 255, 255, 255),
            outline=(200, 200, 205, 255),
            width=1
        )

        # Screen area
        draw.rectangle(
            [(0, chrome_height), (width, height)],
            fill=(0, 0, 0, 255)
        )

        return frame

    def generate_metadata(self, url: str, description: str, ai_description: str = None) -> Dict:
        """Generate metadata for screenshot"""
        return {
            'url': url,
            'description': description or 'Screenshot',
            'ai_description': ai_description,
            'timestamp': datetime.now().isoformat(),
            'project_id': self.project_id
        }

    def save_screenshot(self,
                       frame_image: Image.Image,
                       metadata: Dict,
                       device_type: str,
                       page_name: str) -> str:
        """Save screenshot with metadata"""
        # Create device-specific folder
        device_folder = Path(self.output_dir) / device_type
        device_folder.mkdir(exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_page_name = "".join(c for c in page_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_page_name = safe_page_name.replace(' ', '_')

        filename = f"{safe_page_name}_{timestamp}.png"
        filepath = device_folder / filename

        # Save PNG with transparency
        frame_image.save(filepath, 'PNG', optimize=True)

        # Save metadata
        metadata_file = filepath.with_suffix('.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.screenshots.append({
            'device': device_type,
            'page': page_name,
            'file': str(filepath),
            'metadata_file': str(metadata_file),
            'metadata': metadata
        })

        return str(filepath)

    def create_zip_archive(self, output_filename: str = None) -> str:
        """Create ZIP archive organized by device type"""
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"screenshots_{self.project_id}_{timestamp}.zip"

        zip_path = Path(self.output_dir).parent / output_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add README
            readme_content = self._generate_readme()
            zipf.writestr('README.txt', readme_content)

            # Add all screenshots organized by device type
            for screenshot in self.screenshots:
                device = screenshot['device']
                file_path = Path(screenshot['file'])
                metadata_path = Path(screenshot['metadata_file'])

                # Add to ZIP with device folder structure
                arcname_img = f"{device}/{file_path.name}"
                arcname_meta = f"{device}/{metadata_path.name}"

                zipf.write(file_path, arcname_img)
                zipf.write(metadata_path, arcname_meta)

        return str(zip_path)

    def _generate_readme(self) -> str:
        """Generate README for screenshot package"""
        return f"""AlphaTest Screenshot Package
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Project: {self.project_id}

This package contains marketing screenshots organized by device type.

Folder Structure:
- macbook/    - MacBook Pro screenshots
- iphone/     - iPhone 15 Pro screenshots
- android/    - Pixel 8 Pro screenshots
- ipad/       - iPad Pro screenshots
- desktop/    - Desktop browser screenshots

Each screenshot has:
- .png file (transparent background, high resolution)
- .json file (metadata with URL, description, AI analysis)

Total Screenshots: {len(self.screenshots)}

Usage:
1. Extract the ZIP file
2. Navigate to device-specific folders
3. Use PNG files in your marketing materials
4. Refer to JSON files for context and descriptions

All images have transparent backgrounds and can be overlaid on websites,
presentations, or marketing materials.

Generated by AlphaTest - AI-Powered UAT Testing
https://alphatest.org
"""

    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if Path(self.output_dir).exists():
            shutil.rmtree(self.output_dir)


def generate_ai_description(screenshot_bytes: bytes, anthropic_api_key: str) -> str:
    """Generate AI description of screenshot using Claude Vision"""
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    # Encode screenshot as base64
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64
                    }
                },
                {
                    "type": "text",
                    "text": "Describe this screenshot in 2-3 sentences for marketing purposes. Focus on the main features, layout, and purpose of the page."
                }
            ]
        }]
    )

    return message.content[0].text

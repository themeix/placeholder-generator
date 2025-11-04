# macOS Homebrew Cairo path configuration - MUST be first
import os
import sys

if os.name == 'posix' and 'DYLD_LIBRARY_PATH' not in os.environ:
    os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import streamlit as st
import json
import re
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
from urllib.parse import urlparse
import tempfile
from typing import List, Dict, Set, Optional, Tuple

# Try to import cairosvg with fallback
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Image Placeholder Manager",
    page_icon="🖼️",
    layout="wide"
)

def extract_image_urls(json_content: str) -> Set[str]:
    """Extract image URLs from JSON content, handling complex nested structures."""
    urls = set()
    
    # Common image extensions - expanded list
    image_extensions = r'\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|tif|ico|avif|heic|heif)'
    
    # Use the working pattern for escaped URLs (with \/ escaping)
    escaped_url_pattern = r'https?:\\/\\/[^"\'<>]+\.(?:jpg|jpeg|png|gif|bmp|webp|svg|tiff|tif|ico|avif|heic|heif)'
    escaped_urls = re.findall(escaped_url_pattern, json_content, re.IGNORECASE)
    
    # Clean up escaped URLs by replacing \/ with /
    cleaned_escaped_urls = [url.replace('\\/', '/') for url in escaped_urls]
    
    # Also try direct URLs (without escaping)
    direct_url_pattern = r'https?://[^"\'<>\s]+(?:' + image_extensions + ')'
    direct_urls = re.findall(direct_url_pattern, json_content, re.IGNORECASE)
    
    # Combine all URLs
    all_urls = cleaned_escaped_urls + direct_urls
    
    # Clean and validate URLs
    clean_urls = set()
    for url in all_urls:
        # Remove any trailing characters that might not be part of the URL
        url = re.sub(r'["\',;}\]]+$', '', url)
        # Validate URL format
        if re.match(r'https?://.+\..+', url):
            clean_urls.add(url)
    
    return clean_urls

def get_image_from_url(url: str) -> Optional[Tuple[Image.Image, str]]:
    """Download and return PIL Image from URL with format info."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        # Check if it's an SVG file
        if url.lower().endswith('.svg') or 'svg' in content_type:
            if CAIROSVG_AVAILABLE:
                try:
                    # Try to get SVG dimensions
                    svg_content = response.content
                    
                    # Parse SVG to get width/height
                    import xml.etree.ElementTree as ET
                    try:
                        root = ET.fromstring(svg_content)
                        width = root.get('width', '400')
                        height = root.get('height', '300')
                        
                        # Remove 'px' or other units and extract numbers
                        width = int(re.sub(r'[^\d]', '', str(width)) or 400)
                        height = int(re.sub(r'[^\d]', '', str(height)) or 300)
                        
                        # Ensure reasonable dimensions
                        width = max(100, min(width, 2000))
                        height = max(100, min(height, 2000))
                    except:
                        width, height = 400, 300
                    
                    # Convert SVG to PNG with proper dimensions
                    png_data = cairosvg.svg2png(
                        bytestring=svg_content,
                        output_width=width,
                        output_height=height
                    )
                    img = Image.open(io.BytesIO(png_data))
                    return img, 'SVG'
                    
                except Exception as svg_error:
                    st.warning(f"SVG conversion error for {url}: {str(svg_error)}")
                    return create_placeholder(400, 300, "#CCCCCC", add_text=True), 'SVG'
            else:
                st.info(f"SVG detected but cairosvg not available: {url}")
                return create_placeholder(400, 300, "#CCCCCC", add_text=True), 'SVG'
        
        # Handle regular image formats
        img = Image.open(io.BytesIO(response.content))
        
        # Detect actual format from image
        actual_format = img.format or 'JPEG'
        
        # Handle WebP specially
        if actual_format == 'WEBP':
            # WebP can have transparency
            if img.mode in ('RGBA', 'LA', 'P'):
                st.info(f"WebP with transparency detected: {url}")
        
        return img, actual_format
            
    except requests.RequestException as e:
        st.error(f"Network error: {url} - {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error loading: {url} - {str(e)}")
        return None

def get_filename_from_url(url: str) -> str:
    """Extract filename from URL, handling edge cases."""
    try:
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1]
        if not filename or '.' not in filename:
            return f"image_{hash(url) % 10000}.jpg"
        return filename
    except:
        return f"image_{hash(url) % 10000}.jpg"


def generate_placeholder_filename(original_filename: str, pattern: str, prefix: str, index: int = 1) -> str:
    """Generate placeholder filename based on pattern and settings."""
    # Get base name and extension
    if '.' in original_filename:
        name, ext = original_filename.rsplit('.', 1)
    else:
        name, ext = original_filename, 'png'
    
    # Clean prefix (remove trailing underscore if present)
    clean_prefix = prefix.rstrip('_') if prefix else ""
    
    if pattern == "original_filename":
        if clean_prefix:
            return f"{clean_prefix}_{original_filename}"
        else:
            return f"{name}.png"  # Convert to PNG for placeholder
    
    elif pattern == "prefix_original_filename":
        if clean_prefix:
            return f"{clean_prefix}_{original_filename}"
        else:
            return f"{name}.png"
    
    elif pattern == "original_filename_suffix":
        suffix = clean_prefix if clean_prefix else "placeholder"
        return f"{name}_{suffix}.png"
    
    elif pattern == "prefix_index_original_filename":
        index_str = f"{index:03d}"  # 001, 002, etc.
        if clean_prefix:
            return f"{clean_prefix}_{index_str}_{original_filename}"
        else:
            return f"{index_str}_{name}.png"
    
    # Default fallback
    return f"placeholder_{name}.png"

def create_placeholder(width: int, height: int, color: str, add_text: bool = True) -> Image.Image:
    """Create a placeholder image with specified dimensions and color."""
    # Create image with solid color
    img = Image.new('RGB', (width, height), color)
    
    if add_text:
        draw = ImageDraw.Draw(img)
        text = "Placeholder"
        
        # Calculate font size based on image dimensions
        font_size = min(width, height) // 10
        font_size = max(20, min(font_size, 100))  # Clamp between 20 and 100
        
        try:
            # Try to use a default font
            font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center the text
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text with contrasting color
        text_color = "white" if color.lower() in ["black", "#000000", "#000"] else "black"
        draw.text((x, y), text, fill=text_color, font=font)
    
    return img

def get_image_format_from_image(img: Image.Image, url: str) -> str:
    """Get format from actual image object, fallback to URL."""
    if img.format:
        return img.format
    
    # Fallback to URL extension
    url_lower = url.lower()
    if '.png' in url_lower:
        return 'PNG'
    elif '.webp' in url_lower:
        return 'WEBP'
    elif '.gif' in url_lower:
        return 'GIF'
    else:
        return 'JPEG'

def image_to_bytes(img: Image.Image, format: str = None, quality: int = 85, png_compression: int = 6) -> bytes:
    """Convert PIL Image to bytes with proper format handling."""
    img_bytes = io.BytesIO()
    
    # Default to PNG if no format or SVG
    if format is None or format == 'SVG':
        format = "PNG"
    
    # WebP handling - preserve transparency
    if format.upper() == 'WEBP':
        if img.mode in ('RGBA', 'LA'):
            # Keep as PNG to preserve transparency
            img.save(img_bytes, format='PNG', compress_level=png_compression, optimize=True)
        else:
            # Can convert to JPEG for smaller size
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
    
    # JPEG handling - remove transparency
    elif format.upper() == 'JPEG':
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
    
    # PNG handling
    elif format.upper() == 'PNG':
        img.save(img_bytes, format='PNG', compress_level=png_compression, optimize=True)
    
    # Other formats
    else:
        img.save(img_bytes, format=format)
    
    return img_bytes.getvalue()

def create_zip_file(files: Dict[str, bytes]) -> bytes:
    """Create a ZIP file from a dictionary of filename: content pairs."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)
    return zip_buffer.getvalue()

def get_json_files() -> List[str]:
    """Get list of JSON files from the json directory."""
    json_dir = os.path.join(os.getcwd(), "json")
    if not os.path.exists(json_dir):
        return []
    
    json_files = []
    for file in os.listdir(json_dir):
        if file.endswith('.json'):
            json_files.append(file)
    
    return sorted(json_files)

def main():
    st.title("🖼️ Image Placeholder Manager")
    st.markdown("Upload a JSON file to load images and manage placeholders.")
    
    # Initialize session state
    if 'image_urls' not in st.session_state:
        st.session_state.image_urls = set()
    if 'images_data' not in st.session_state:
        st.session_state.images_data = {}
    if 'placeholders_data' not in st.session_state:
        st.session_state.placeholders_data = {}
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = None
    if 'failed_downloads' not in st.session_state:
        st.session_state.failed_downloads = {}
    
    # Clear/Reset button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Clear All & Start Over"):
            for key in ['image_urls', 'images_data', 'placeholders_data', 'selected_file', 'failed_downloads']:
                st.session_state.pop(key, None)
            st.rerun()
    
    # Main tabs organization
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "⚙️ Process", "📥 Download", "🛠️ Settings"])
    
    with tab1:
        # JSON file upload section (directory selection removed)
        st.header("📤 Upload JSON File")
        
        json_content = None
        selected_file_name = None
        
        uploaded_file = st.file_uploader(
            "Upload a JSON file",
            type=['json'],
            help="Upload a JSON file containing image URLs"
        )
        
        if uploaded_file is not None:
            selected_file_name = uploaded_file.name
            try:
                # Read uploaded file content
                json_content = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError as e:
                st.error(f"Encoding error reading uploaded file: {str(e)}")
            except Exception as e:
                st.error(f"Error reading uploaded file: {str(e)}")
        
        # Process the uploaded file and auto-load images
        if json_content and selected_file_name:
            st.session_state.selected_file = selected_file_name
            
            try:
                # Store JSON content in session state for later use
                st.session_state.json_content = json_content
                
                # Show file info
                file_size = len(json_content.encode('utf-8'))
                st.info(f"**{selected_file_name}** - {file_size / (1024*1024):.1f}MB")
                
                # Extract image URLs
                urls = extract_image_urls(json_content)
                
                if urls:
                    # Reset previous state when a new file is uploaded
                    st.session_state.image_urls = urls
                    st.session_state.images_data = {}
                    st.session_state.placeholders_data = {}
                    st.session_state.failed_downloads = {}
                    st.success(f"Found {len(urls)} unique image URLs")
                    
                    # Export URLs button
                    urls_text = "\n".join(sorted(urls))
                    st.download_button(
                        label="📄 Export URLs to Text File",
                        data=urls_text,
                        file_name="extracted_image_urls.txt",
                        mime="text/plain",
                        help="Download all extracted image URLs as a text file"
                    )
                    
                    # Auto-load images immediately
                    urls_list = list(st.session_state.image_urls)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, url in enumerate(urls_list):
                        status_text.text(f"Loading image {idx + 1} of {len(urls_list)}: {get_filename_from_url(url)}")
                        result = get_image_from_url(url)
                        if result:
                            img, format_info = result
                            st.session_state.images_data[url] = {
                                'image': img,
                                'format': format_info
                            }
                        else:
                            st.session_state.failed_downloads[url] = "Failed to load image"
                        progress_bar.progress((idx + 1) / len(urls_list))
                    
                    status_text.text("✅ Loading complete!")
                    st.success(f"Loaded {len(st.session_state.images_data)} images successfully")
                    
                    # Show failed downloads if any
                    if st.session_state.failed_downloads:
                        with st.expander(f"⚠️ {len(st.session_state.failed_downloads)} Failed Downloads"):
                            for url, error in st.session_state.failed_downloads.items():
                                st.error(f"{get_filename_from_url(url)}: {error}")
                    
                    # Display a quick preview grid of loaded images
                    if st.session_state.images_data:
                        st.subheader("🖼️ Loaded Images Preview")
                        urls_list = list(st.session_state.image_urls)
                        for i in range(0, len(urls_list), 4):
                            cols = st.columns(4)
                            for j, col in enumerate(cols):
                                if i + j < len(urls_list):
                                    url = urls_list[i + j]
                                    img_data = st.session_state.images_data.get(url)
                                    if img_data:
                                        img = img_data['image']
                                        with col:
                                            st.image(img, use_container_width=True)
                                            filename = get_filename_from_url(url)
                                            st.caption(f"**{filename}**")
                else:
                    st.warning("No image URLs found in the JSON file")
                    st.session_state.image_urls = set()
                    st.session_state.images_data = {}
                    
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {str(e)}")
                st.session_state.image_urls = set()
                st.session_state.images_data = {}
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                st.session_state.image_urls = set()
                st.session_state.images_data = {}
    
    with tab2:
        # Process tab - Image loading and placeholder generation
        if st.session_state.image_urls:
            st.header("🔄 Process Images")
            
            # Auto-load images if not already loaded (no button)
            if not st.session_state.images_data:
                urls = list(st.session_state.image_urls)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                st.session_state.images_data = {}
                st.session_state.failed_downloads = {}
                
                for idx, url in enumerate(urls):
                    status_text.text(f"Loading image {idx + 1} of {len(urls)}: {get_filename_from_url(url)}")
                    result = get_image_from_url(url)
                    if result:
                        img, format_info = result
                        st.session_state.images_data[url] = {
                            'image': img,
                            'format': format_info
                        }
                    else:
                        st.session_state.failed_downloads[url] = "Failed to load image"
                    progress_bar.progress((idx + 1) / len(urls))
                
                status_text.text("✅ Loading complete!")
                st.success(f"Loaded {len(st.session_state.images_data)} images successfully")
                
                # Show failed downloads if any
                if st.session_state.failed_downloads:
                    with st.expander(f"⚠️ {len(st.session_state.failed_downloads)} Failed Downloads"):
                        for url, error in st.session_state.failed_downloads.items():
                            st.error(f"{get_filename_from_url(url)}: {error}")
            else:
                st.success(f"✅ {len(st.session_state.images_data)} images loaded")
                
                # Show image statistics
                if st.session_state.images_data:
                    total_size_mb = sum(len(image_to_bytes(img_data['image'])) for img_data in st.session_state.images_data.values()) / (1024 * 1024)
                    avg_width = sum(img_data['image'].width for img_data in st.session_state.images_data.values()) // len(st.session_state.images_data)
                    avg_height = sum(img_data['image'].height for img_data in st.session_state.images_data.values()) // len(st.session_state.images_data)
                    unique_formats = set(img_data['format'] for img_data in st.session_state.images_data.values())
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Images", len(st.session_state.images_data))
                    col2.metric("Total Size", f"{total_size_mb:.1f} MB")
                    col3.metric("Avg Dimensions", f"{avg_width}×{avg_height}")
                    col4.metric("Formats", ", ".join(unique_formats))
            
            # Placeholder generation section
            if st.session_state.images_data:
                st.subheader("🎨 Generate Placeholders")
                
                col1, col2 = st.columns(2)
                with col1:
                    placeholder_color = st.color_picker("Placeholder Color", "#CCCCCC")
                with col2:
                    placeholder_text = st.text_input("Placeholder Text", value="Placeholder")
                
                # Generate placeholders button
                if st.button("Generate Placeholders", type="primary"):
                    with st.spinner("Generating placeholders..."):
                        st.session_state.placeholders_data = {}
                        for url, img_data in st.session_state.images_data.items():
                            img = img_data['image']
                            placeholder = create_placeholder(
                                img.width, img.height, placeholder_color, add_text=bool(placeholder_text)
                            )
                            # Update placeholder text if custom text provided
                            if placeholder_text != "Placeholder":
                                placeholder = create_placeholder_with_custom_text(
                                    img.width, img.height, placeholder_color, placeholder_text
                                )
                            st.session_state.placeholders_data[url] = placeholder
                        st.success("Placeholders generated successfully!")
        else:
            st.info("Please upload and process a JSON file first in the Upload tab.")
    
    with tab3:
        # Download tab
        if st.session_state.images_data:
            st.header("📦 Downloads")
            
            # Batch download buttons
            if st.session_state.placeholders_data:
                st.subheader("📦 Batch Downloads")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Download All Originals (ZIP)"):
                        with st.spinner("Creating ZIP file..."):
                            files = {}
                            for url, img_data in st.session_state.images_data.items():
                                img = img_data['image']
                                format_info = img_data['format']
                                filename = get_filename_from_url(url)
                                files[filename] = image_to_bytes(img, format_info)
                            
                            zip_data = create_zip_file(files)
                            st.download_button(
                                label="📥 Download Originals ZIP",
                                data=zip_data,
                                file_name="original_images.zip",
                                mime="application/zip"
                            )
                
                with col2:
                    if st.button("Download All Placeholders (ZIP)"):
                        with st.spinner("Creating ZIP file..."):
                            files = {}
                            naming_pattern = st.session_state.get('naming_pattern', 'original_filename')
                            custom_prefix = st.session_state.get('custom_prefix', '')
                            for i, (url, placeholder) in enumerate(st.session_state.placeholders_data.items()):
                                original_filename = get_filename_from_url(url)
                                placeholder_filename = generate_placeholder_filename(original_filename, naming_pattern, custom_prefix, i+1)
                                files[placeholder_filename] = image_to_bytes(placeholder, "PNG")
                            
                            zip_data = create_zip_file(files)
                            st.download_button(
                                label="📥 Download Placeholders ZIP",
                                data=zip_data,
                                file_name="placeholder_images.zip",
                                mime="application/zip"
                            )
            
            # Individual image downloads
            st.subheader("🖼️ Individual Downloads")
            
            # Comparison view toggle
            show_comparison = st.checkbox("Show Side-by-Side Comparison")
            
            if st.session_state.images_data:
                # Display images in grid
                urls_list = list(st.session_state.image_urls)
                
                for i in range(0, len(urls_list), 2 if show_comparison else 4):
                    if show_comparison:
                        cols = st.columns(2)
                        for j, col in enumerate(cols):
                            if i + j < len(urls_list):
                                url = urls_list[i + j]
                                img_data = st.session_state.images_data.get(url)
                                
                                if img_data:
                                    img = img_data['image']
                                    with col:
                                        # Side-by-side comparison
                                        comp_col1, comp_col2 = st.columns(2)
                                        with comp_col1:
                                            st.image(img, caption="Original", use_container_width=True)
                                        with comp_col2:
                                            if url in st.session_state.placeholders_data:
                                                placeholder = st.session_state.placeholders_data[url]
                                                st.image(placeholder, caption="Placeholder", use_container_width=True)
                                            else:
                                                st.info("Generate placeholder first")
                                        
                                        # Download buttons
                                        filename = get_filename_from_url(url)
                                        st.caption(f"**{filename}** - {img.width}×{img.height}")
                                        
                                        # Three download buttons
                                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                                        
                                        with btn_col1:
                                            format_info = img_data['format']
                                            original_bytes = image_to_bytes(img, format_info)
                                            st.download_button(
                                                label="📥 Original",
                                                data=original_bytes,
                                                file_name=filename,
                                                mime=f"image/{format_info.lower()}",
                                                key=f"orig_comp_{i}_{j}"
                                            )
                                        
                                        with btn_col2:
                                            st.link_button(
                                                label="🌐 Remote",
                                                url=url,
                                                help="Open original image URL"
                                            )
                                        
                                        with btn_col3:
                                            if url in st.session_state.placeholders_data:
                                                placeholder = st.session_state.placeholders_data[url]
                                                placeholder_bytes = image_to_bytes(placeholder, "PNG")
                                                # Use new naming pattern function
                                                naming_pattern = st.session_state.get('naming_pattern', 'original_filename')
                                                custom_prefix = st.session_state.get('custom_prefix', '')
                                                placeholder_filename = generate_placeholder_filename(filename, naming_pattern, custom_prefix, i*4+j+1)
                                                st.download_button(
                                                    label="📥 Placeholder",
                                                    data=placeholder_bytes,
                                                    file_name=placeholder_filename,
                                                    mime="image/png",
                                                    key=f"place_comp_{i}_{j}"
                                                )
                                            else:
                                                st.button("Generate First", disabled=True, key=f"disabled_comp_{i}_{j}")
                    else:
                        # Regular grid view (4 per row)
                        cols = st.columns(4)
                        for j, col in enumerate(cols):
                            if i + j < len(urls_list):
                                url = urls_list[i + j]
                                img_data = st.session_state.images_data.get(url)
                                
                                if img_data:
                                    img = img_data['image']
                                    with col:
                                        # Display image
                                        st.image(img, use_container_width=True)
                                        
                                        # Filename and info
                                        filename = get_filename_from_url(url)
                                        st.caption(f"**{filename}**")
                                        st.caption(f"Size: {img.width}x{img.height}")
                                        
                                        # Three download buttons
                                        btn_col1, btn_col2, btn_col3 = st.columns(3)
                                        
                                        with btn_col1:
                                            format_info = img_data['format']
                                            original_bytes = image_to_bytes(img, format_info)
                                            st.download_button(
                                                label="📥 Orig",
                                                data=original_bytes,
                                                file_name=filename,
                                                mime=f"image/{format_info.lower()}",
                                                key=f"orig_{i}_{j}",
                                                help="Download original image"
                                            )
                                        
                                        with btn_col2:
                                            st.link_button(
                                                label="🌐 URL",
                                                url=url,
                                                help="Open original image URL"
                                            )
                                        
                                        with btn_col3:
                                            if url in st.session_state.placeholders_data:
                                                placeholder = st.session_state.placeholders_data[url]
                                                placeholder_bytes = image_to_bytes(placeholder, "PNG")
                                                # Use new naming pattern function
                                                naming_pattern = st.session_state.get('naming_pattern', 'original_filename')
                                                custom_prefix = st.session_state.get('custom_prefix', '')
                                                placeholder_filename = generate_placeholder_filename(filename, naming_pattern, custom_prefix, i*4+j+1)
                                                st.download_button(
                                                    label="📥 Place",
                                                    data=placeholder_bytes,
                                                    file_name=placeholder_filename,
                                                    mime="image/png",
                                                    key=f"place_{i}_{j}",
                                                    help="Download placeholder image"
                                                )
                                            else:
                                                st.button("Gen First", disabled=True, key=f"disabled_{i}_{j}", help="Generate placeholder first")
        else:
            st.info("No images loaded. Please process images first in the Process tab.")
    
    with tab4:
        # Settings tab
        st.header("🛠️ Settings")
        
        # Image optimization settings
        st.subheader("🎛️ Image Quality Settings")
        col1, col2 = st.columns(2)
        with col1:
            jpeg_quality = st.slider("JPEG Quality", 50, 100, 85, help="Higher values = better quality, larger file size")
        with col2:
            png_compression = st.slider("PNG Compression", 0, 9, 6, help="Higher values = smaller file size, slower compression")
        
        # Batch rename options
        st.subheader("📝 Naming Patterns")
        
        # Custom prefix input
        custom_prefix = st.text_input(
            "Custom Prefix (optional)",
            value="placeholder_",
            help="Add a custom prefix to placeholder filenames. Leave empty for no prefix."
        )
        
        naming_pattern = st.selectbox(
            "Placeholder Naming Pattern",
            [
                "original_filename",  # Default: keep original name with prefix
                "prefix_original_filename", 
                "original_filename_suffix",
                "prefix_index_original_filename"
            ],
            index=0,  # Default to original filename
            help="Choose how placeholder files should be named"
        )
        
        # Show example of naming pattern
        example_filename = "69555-author.webp"
        if naming_pattern == "original_filename":
            if custom_prefix:
                example_result = f"{custom_prefix}{example_filename}"
            else:
                example_result = example_filename
        elif naming_pattern == "prefix_original_filename":
            example_result = f"{custom_prefix}{example_filename}" if custom_prefix else example_filename
        elif naming_pattern == "original_filename_suffix":
            name, ext = example_filename.rsplit('.', 1) if '.' in example_filename else (example_filename, 'png')
            suffix = custom_prefix.rstrip('_') if custom_prefix else "placeholder"
            example_result = f"{name}_{suffix}.{ext}"
        elif naming_pattern == "prefix_index_original_filename":
            example_result = f"{custom_prefix}001_{example_filename}" if custom_prefix else f"001_{example_filename}"
        
        st.info(f"**Example:** `{example_filename}` → `{example_result}`")
        
        # Memory management settings
        st.subheader("💾 Memory Management")
        max_image_size = st.slider("Max Image Dimension (pixels)", 500, 4000, 2000, 
                                 help="Images larger than this will be resized to save memory")
        max_total_size = st.slider("Max Total Size (MB)", 50, 500, 200,
                                 help="Stop loading images when total size exceeds this limit")
        
        # Store settings in session state
        st.session_state.jpeg_quality = jpeg_quality
        st.session_state.png_compression = png_compression
        st.session_state.naming_pattern = naming_pattern
        st.session_state.custom_prefix = custom_prefix
        st.session_state.max_image_size = max_image_size
        st.session_state.max_total_size = max_total_size
        
        # JSON Updater section
        if st.session_state.placeholders_data:
            st.subheader("🔄 JSON Updater")
            st.markdown("Replace original image URLs with placeholder URLs in your JSON.")
            
            base_url = st.text_input(
                "Base URL for hosted placeholders",
                value="https://diviflow.com/placeholder/images/",
                help="Enter the base URL where your placeholder images will be hosted"
            )
            
            if base_url and st.button("Generate Updated JSON"):
                try:
                    # Parse original JSON from session state
                    original_json = json.loads(st.session_state.json_content)
                    updated_json_str = json.dumps(original_json, indent=2)
                    
                    # Replace URLs
                    for i, url in enumerate(st.session_state.image_urls):
                        filename = get_filename_from_url(url)
                        # Use new naming pattern function
                        naming_pattern = st.session_state.get('naming_pattern', 'original_filename')
                        custom_prefix = st.session_state.get('custom_prefix', '')
                        placeholder_filename = generate_placeholder_filename(filename, naming_pattern, custom_prefix, i+1)
                        new_url = base_url.rstrip('/') + '/' + placeholder_filename
                        updated_json_str = updated_json_str.replace(url, new_url)
                    
                    # Display updated JSON
                    st.subheader("Updated JSON")
                    st.code(updated_json_str, language="json")
                    
                    # Download button for updated JSON
                    st.download_button(
                        label="📥 Download Updated JSON",
                        data=updated_json_str,
                        file_name="updated_with_placeholders.json",
                        mime="application/json"
                    )
                    
                except json.JSONDecodeError as e:
                    st.error(f"JSON parsing error: {str(e)}")
                except Exception as e:
                    st.error(f"Error updating JSON: {str(e)}")

def create_placeholder_with_custom_text(width: int, height: int, color: str, text: str) -> Image.Image:
    """Create a placeholder image with custom text."""
    # Create image with solid color
    img = Image.new('RGB', (width, height), color)
    
    draw = ImageDraw.Draw(img)
    
    # Calculate font size based on image dimensions
    font_size = min(width, height) // 10
    font_size = max(20, min(font_size, 100))  # Clamp between 20 and 100
    
    try:
        # Try to use a default font
        font = ImageFont.truetype("Arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text with contrasting color
    text_color = "white" if color.lower() in ["black", "#000000", "#000"] else "black"
    draw.text((x, y), text, fill=text_color, font=font)
    
    return img

if __name__ == "__main__":
    main()
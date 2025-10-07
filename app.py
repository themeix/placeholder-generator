import streamlit as st
import json
import re
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
from urllib.parse import urlparse
import tempfile
from typing import List, Dict, Set

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

def get_image_from_url(url: str) -> Image.Image:
    """Download and return PIL Image from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Check if it's an SVG file
        if url.lower().endswith('.svg') or 'svg' in response.headers.get('content-type', '').lower():
            # For SVG files, create a placeholder image instead of trying to convert
            st.warning(f"SVG file detected: {url}. Creating placeholder instead.")
            return create_placeholder(400, 300, "#CCCCCC", add_text=True)
        else:
            # Handle regular image formats
            return Image.open(io.BytesIO(response.content))
            
    except Exception as e:
        st.error(f"Error loading image from {url}: {str(e)}")
        return None

def get_filename_from_url(url: str) -> str:
    """Extract filename from URL."""
    parsed = urlparse(url)
    return os.path.basename(parsed.path)

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

def image_to_bytes(img: Image.Image, format: str = "PNG") -> bytes:
    """Convert PIL Image to bytes."""
    img_bytes = io.BytesIO()
    
    # Convert RGBA to RGB if saving as JPEG
    if format.upper() == "JPEG" and img.mode == "RGBA":
        # Create a white background
        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
        img = rgb_img
    
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
    st.markdown("Select a JSON file from the `/json/` directory to generate placeholders and manage downloads.")
    
    # Initialize session state
    if 'image_urls' not in st.session_state:
        st.session_state.image_urls = set()
    if 'images_data' not in st.session_state:
        st.session_state.images_data = {}
    if 'placeholders_data' not in st.session_state:
        st.session_state.placeholders_data = {}
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = None
    
    # JSON file selection section
    st.header("📁 Select JSON File")
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["📂 Select from Directory", "📤 Upload File"])
    
    json_content = None
    selected_file_name = None
    
    with tab1:
        json_files = get_json_files()
        
        if not json_files:
            st.warning("No JSON files found in the `/json/` directory.")
        else:
            # File selection dropdown
            selected_file = st.selectbox(
                "Choose a JSON file:",
                options=[""] + json_files,
                index=0 if st.session_state.selected_file is None else json_files.index(st.session_state.selected_file) + 1,
                key="dropdown_select"
            )
            
            if selected_file:
                selected_file_name = selected_file
                # Read JSON content from directory
                json_path = os.path.join("json", selected_file)
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_content = f.read()
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
    
    with tab2:
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
            except Exception as e:
                st.error(f"Error reading uploaded file: {str(e)}")
    
    # Process the selected/uploaded file
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
                st.session_state.image_urls = urls
                st.success(f"Found {len(urls)} unique image URLs")
                
                # Add export URLs to text file button
                urls_text = "\n".join(sorted(urls))
                st.download_button(
                    label="📄 Export URLs to Text File",
                    data=urls_text,
                    file_name="extracted_image_urls.txt",
                    mime="text/plain",
                    help="Download all extracted image URLs as a text file"
                )
                
                # Load images
                with st.spinner("Loading images..."):
                    st.session_state.images_data = {}  # Reset images data
                    for url in urls:
                        img = get_image_from_url(url)
                        if img:
                            st.session_state.images_data[url] = img
            else:
                st.warning("No image URLs found in the JSON file")
                st.session_state.image_urls = set()
                st.session_state.images_data = {}
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.session_state.image_urls = set()
            st.session_state.images_data = {}
    
    # Placeholder settings
    if st.session_state.image_urls:
        st.header("🎨 Placeholder Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            placeholder_color = st.color_picker("Placeholder Color", "#CCCCCC")
        with col2:
            add_text = st.checkbox("Add 'Placeholder' text", value=True)
        
        # Generate placeholders button
        if st.button("Generate Placeholders", type="primary"):
            with st.spinner("Generating placeholders..."):
                st.session_state.placeholders_data = {}
                for url, img in st.session_state.images_data.items():
                    placeholder = create_placeholder(
                        img.width, img.height, placeholder_color, add_text
                    )
                    st.session_state.placeholders_data[url] = placeholder
                st.success("Placeholders generated successfully!")
        
        # Batch download buttons
        if st.session_state.placeholders_data:
            st.header("📦 Batch Downloads")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Download All Originals (ZIP)"):
                    with st.spinner("Creating ZIP file..."):
                        files = {}
                        for url, img in st.session_state.images_data.items():
                            filename = get_filename_from_url(url)
                            files[filename] = image_to_bytes(img, "JPEG")
                        
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
                        for url, placeholder in st.session_state.placeholders_data.items():
                            filename = f"placeholder_{get_filename_from_url(url)}"
                            files[filename] = image_to_bytes(placeholder, "PNG")
                        
                        zip_data = create_zip_file(files)
                        st.download_button(
                            label="📥 Download Placeholders ZIP",
                            data=zip_data,
                            file_name="placeholder_images.zip",
                            mime="application/zip"
                        )
        
        # Image grid display
        st.header("🖼️ Image Gallery")
        
        if st.session_state.images_data:
            # Display images in grid (4 per row)
            urls_list = list(st.session_state.image_urls)
            
            for i in range(0, len(urls_list), 4):
                cols = st.columns(4)
                
                for j, col in enumerate(cols):
                    if i + j < len(urls_list):
                        url = urls_list[i + j]
                        img = st.session_state.images_data.get(url)
                        
                        if img:
                            with col:
                                # Display image
                                st.image(img, use_container_width=True)
                                
                                # Filename
                                filename = get_filename_from_url(url)
                                st.caption(f"**{filename}**")
                                st.caption(f"Size: {img.width}x{img.height}")
                                
                                # Download buttons
                                col_a, col_b = st.columns(2)
                                
                                with col_a:
                                    original_bytes = image_to_bytes(img, "JPEG")
                                    st.download_button(
                                        label="📥 Original",
                                        data=original_bytes,
                                        file_name=filename,
                                        mime="image/jpeg",
                                        key=f"orig_{i}_{j}"
                                    )
                                
                                with col_b:
                                    if url in st.session_state.placeholders_data:
                                        placeholder = st.session_state.placeholders_data[url]
                                        placeholder_bytes = image_to_bytes(placeholder, "PNG")
                                        placeholder_filename = f"placeholder_{filename.rsplit('.', 1)[0]}.png"
                                        st.download_button(
                                            label="📥 Placeholder",
                                            data=placeholder_bytes,
                                            file_name=placeholder_filename,
                                            mime="image/png",
                                            key=f"place_{i}_{j}"
                                        )
                                    else:
                                        st.button("Generate First", disabled=True, key=f"disabled_{i}_{j}")
        
        # JSON Updater section
        if st.session_state.placeholders_data:
            st.header("🔄 JSON Updater")
            st.markdown("Replace original image URLs with placeholder URLs in your JSON.")
            
            base_url = st.text_input(
                "Base URL for hosted placeholders",
                value="https://diviflow.com/palceholder/images/",
                help="Enter the base URL where your placeholder images will be hosted"
            )
            
            if base_url and st.button("Generate Updated JSON"):
                try:
                    # Parse original JSON from session state
                    original_json = json.loads(st.session_state.json_content)
                    updated_json_str = json.dumps(original_json, indent=2)
                    
                    # Replace URLs
                    for url in st.session_state.image_urls:
                        filename = get_filename_from_url(url)
                        placeholder_filename = f"placeholder_{filename.rsplit('.', 1)[0]}.png"
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
                    
                except Exception as e:
                    st.error(f"Error updating JSON: {str(e)}")

if __name__ == "__main__":
    main()
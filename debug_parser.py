#!/usr/bin/env python3
import json
import re
from typing import Set

def extract_image_urls_debug(json_content: str) -> Set[str]:
    """Debug version of extract_image_urls function."""
    urls = set()
    
    # Common image extensions - expanded list
    image_extensions = r'\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff|tif|ico|avif|heic|heif)'
    
    def extract_from_text(text: str):
        """Extract URLs from text content."""
        print(f"Searching in text of length: {len(text)}")
        
        # Pattern for URLs with image extensions
        url_pattern = r'https?://[^\s"\'<>\\]+' + image_extensions
        found_urls = re.findall(url_pattern, text, re.IGNORECASE)
        print(f"Found direct URLs: {found_urls}")
        
        # Also look for escaped URLs (with \/)
        escaped_url_pattern = r'https?:\\?/\\?/[^\s"\'<>]+' + image_extensions
        escaped_urls = re.findall(escaped_url_pattern, text, re.IGNORECASE)
        print(f"Found escaped URLs: {escaped_urls}")
        
        # Clean up escaped URLs
        escaped_urls = [url.replace('\\/', '/').replace('\\', '') for url in escaped_urls]
        print(f"Cleaned escaped URLs: {escaped_urls}")
        
        return found_urls + escaped_urls
    
    def recursive_search(obj, depth=0):
        """Recursively search through JSON object for image URLs."""
        indent = "  " * depth
        print(f"{indent}Searching object type: {type(obj)}")
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                print(f"{indent}Key: {key}")
                # Check if key suggests it might contain image URLs
                if any(img_key in key.lower() for img_key in ['src', 'url', 'image', 'img', 'background', 'photo', 'picture']):
                    print(f"{indent}  -> Image-related key found!")
                    if isinstance(value, str):
                        found = extract_from_text(value)
                        urls.update(found)
                        print(f"{indent}  -> Added {len(found)} URLs")
                recursive_search(value, depth + 1)
        elif isinstance(obj, list):
            print(f"{indent}List with {len(obj)} items")
            for i, item in enumerate(obj):
                print(f"{indent}Item {i}:")
                recursive_search(item, depth + 1)
        elif isinstance(obj, str):
            print(f"{indent}String of length: {len(obj)}")
            # Check if string contains escaped JSON
            if '{' in obj and '}' in obj:
                print(f"{indent}  -> Contains JSON-like content")
                try:
                    # Try to parse as JSON
                    nested_json = json.loads(obj)
                    print(f"{indent}  -> Successfully parsed nested JSON")
                    recursive_search(nested_json, depth + 1)
                except json.JSONDecodeError as e:
                    print(f"{indent}  -> JSON parse failed: {e}")
                    # If not valid JSON, just extract URLs from the string
                    found = extract_from_text(obj)
                    urls.update(found)
                    print(f"{indent}  -> Added {len(found)} URLs from string")
            else:
                found = extract_from_text(obj)
                urls.update(found)
                print(f"{indent}  -> Added {len(found)} URLs from simple string")
    
    print("=== Starting URL extraction ===")
    
    # First, extract URLs directly from the raw content
    print("\n1. Extracting from raw content...")
    raw_urls = extract_from_text(json_content)
    urls.update(raw_urls)
    print(f"Raw extraction found: {len(raw_urls)} URLs")
    
    # Then try to parse as JSON and search recursively
    print("\n2. Parsing as JSON and searching recursively...")
    try:
        parsed_json = json.loads(json_content)
        print("Successfully parsed main JSON")
        recursive_search(parsed_json)
    except json.JSONDecodeError as e:
        print(f"Main JSON parse failed: {e}")
    
    print(f"\n=== Total URLs found: {len(urls)} ===")
    for url in sorted(urls):
        print(f"  - {url}")
    
    return urls

# Test with the Water Flow JSON file
if __name__ == "__main__":
    with open("/Volumes/SSD/Diviflow Projects/placeholder/json/Water Flow - Full Page.json", "r") as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    urls = extract_image_urls_debug(content)
    print(f"\nFinal result: {len(urls)} unique URLs found")
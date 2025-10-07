import re

# Read the file
with open('json/Water Flow - Full Page.json', 'r', encoding='utf-8') as f:
    content = f.read()

print(f'File size: {len(content)} characters')

# Test patterns based on what we see in the actual content
patterns = [
    # Pattern for URLs with \/ escaping (what we see in the JSON)
    r'https?:\\/\\/[^"\'<>]+\.(?:jpg|jpeg|png|gif|bmp|webp|svg|tiff|tif|ico|avif|heic|heif)',
    # Pattern for direct URLs without escaping
    r'https?://[^"\'<>\s]+\.(?:jpg|jpeg|png|gif|bmp|webp|svg|tiff|tif|ico|avif|heic|heif)',
    # More specific pattern for the domains we see
    r'https?:\\/\\/(?:demo\.diviflow\.com|diviflow\.local)[^"\'<>]*\.(?:jpg|jpeg|png|gif|bmp|webp|svg|tiff|tif|ico|avif|heic|heif)',
]

for i, pattern in enumerate(patterns, 1):
    try:
        matches = re.findall(pattern, content, re.IGNORECASE)
        print(f'Pattern {i} matches: {len(matches)}')
        if matches:
            print(f'  First match: {matches[0]}')
            cleaned = matches[0].replace('\\/', '/')
            print(f'  Cleaned: {cleaned}')
    except Exception as e:
        print(f'Pattern {i} error: {e}')
    print()
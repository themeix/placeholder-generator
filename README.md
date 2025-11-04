# 🖼️ Image Placeholder Manager

A powerful Streamlit application for managing image placeholders from JSON files containing image URLs.

## Features

### 📁 Upload & Preview
- Upload JSON files containing image URLs
- Automatic parsing and duplicate handling
- Grid layout display (4 images per row)
- Individual download buttons for originals and placeholders

### 🎨 Placeholder Generator
- Dynamic placeholder generation using Pillow
- Customizable solid colors via color picker
- Optional "Placeholder" text overlay
- Auto-adjusted font sizing based on image dimensions
- Maintains original image dimensions

### 📦 Batch Downloads
- Download all original images as ZIP
- Download all generated placeholders as ZIP
- Organized file naming conventions

### 🔄 JSON Updater
- Replace original URLs with placeholder URLs
- Configurable base URL for hosted placeholders
- Download updated JSON file

## Installation

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Deploying to Streamlit Cloud

This app uses `cairosvg` to convert SVGs to PNGs. `cairosvg` depends on native system libraries (Cairo and Pango). On Streamlit Cloud, you must declare these Linux packages so they are installed at build time.

1. Ensure `requirements.txt` includes:
```txt
cairosvg>=2.7.0
```

2. Add a `packages.txt` file at the repository root with the following contents:
```txt
libcairo2
libpango-1.0-0
libpangocairo-1.0-0
fonts-dejavu-core
```

3. Push and redeploy the app on Streamlit Cloud. The build will install these system libraries, and the `cairosvg` import will succeed.

Troubleshooting:
- If you still see `OSError` related to `libcairo`, confirm the `packages.txt` file is in the repo root and the app was redeployed.
- Check the Cloud build logs for apt installation; if fonts are missing for SVG text rendering, ensure `fonts-dejavu-core` is present.
- The app falls back to placeholders for SVGs if `cairosvg` is unavailable, but installing the above packages enables proper SVG conversion.

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to the provided URL (usually `http://localhost:8501`)

3. Upload a JSON file containing image URLs

4. Configure placeholder settings (color, text)

5. Generate placeholders and download as needed

## JSON Format Support

The app can parse any JSON file and extract image URLs using regex patterns. It supports common image formats:
- JPG/JPEG
- PNG
- GIF
- BMP
- WebP
- SVG

Example JSON structure:
```json
{
  "context": "et_builder",
  "data": {
    "305": "<!-- wp:divi/image {\"image\":{\"innerContent\":{\"desktop\":{\"value\":{\"src\":\"https://demo.diviflow.com/wp-content/uploads/2025/08/Saasflow-logo.svg\"}}}}} -->"
  }
}
```

## Dependencies

- `streamlit>=1.28.0` - Web app framework
- `Pillow>=10.0.0` - Image processing
- `requests>=2.31.0` - HTTP requests for downloading images

## Features in Detail

### Image Processing
- Automatic image dimension detection
- Placeholder generation with matching dimensions
- Smart font sizing algorithm
- Contrasting text colors for readability

### File Management
- Secure temporary file handling
- ZIP compression for batch downloads
- Proper filename extraction from URLs
- Error handling for network requests

### User Interface
- Responsive grid layout
- Progress indicators for long operations
- Color picker for customization
- Real-time preview updates

## Error Handling

The application includes comprehensive error handling for:
- Invalid JSON files
- Network connectivity issues
- Unsupported image formats
- File processing errors

## Browser Compatibility

Tested and compatible with:
- Chrome
- Firefox
- Safari
- Edge

## License

This project is open source and available under the MIT License.
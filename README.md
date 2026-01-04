# photo_slideshow

A CLI tool to create 8K video slideshows from a collection of photos and videos.

## Features
- **High Resolution:** Generates 8K (7680x4320) output videos.
- **EXIF Metadata:** Automatically overlays technical details (ISO, aperture, shutter speed, etc.) on photos.
- **Mixed Media:** Seamlessly combines photos and video clips.
- **Audio Integration:** Adds background music with loop and fade-out effects.

## Prerequisites
This tool relies on the following system packages:
- **FFmpeg**: For video processing and composition.
- **ImageMagick**: For image manipulation and text overlay (`convert`, `identify`).

### Installation of Prerequisites

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install ffmpeg imagemagick
```

**macOS (Homebrew):**
```bash
brew install ffmpeg imagemagick
```

**Windows (Winget):**
```bash
winget install ffmpeg
winget install ImageMagick.ImageMagick
```

## Installation

Clone the repository and install the package:

```bash
pip install .
```

For development (editable install):
```bash
pip install -e .
```

## Usage

Run the command followed by your media directory and audio directory:

```bash
photo-slideshow /path/to/media/files /path/to/audio/files
```

### Quick Demo
You can test the tool using the provided example resources:
```bash
photo-slideshow photos audio
```

### Arguments
- `<media_dir>`: Directory containing `.jpg`, `.jpeg` images and `.mp4`, `.mov` videos. (e.g., the `./photos` directory).
- `<audio_dir>`: Directory containing `.mp3` files for background music. (e.g., the `./audio` directory).

## Output
The script generates:
1. `output.mp4`: The silent slideshow video.
2. `output_audio.mp4`: The final video with background music.
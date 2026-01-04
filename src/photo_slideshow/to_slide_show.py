import sys
import os
import subprocess
import random
import argparse
import concurrent.futures
import shutil
import shlex

TIME_GAP = 5
DURATION = 0.5
OUTPUT_MP4 = "output.mp4"
OUTPUT_AUDIO_MP4 = "output_audio.mp4"
FADE_OUT_LEN = 5

def run_os_command(cmd):
    # print(cmd)
    # Split command string into list for cross-platform compatibility
    # Windows compatibility note: shell=False is generally safer and better, 
    # but exact command parsing might vary. shlex handles POSIX style.
    try:
        args = shlex.split(cmd)
        # Check if running on Windows to handle specific command nuances if needed,
        # but for ffmpeg/convert usually straightforward args work.
        result = subprocess.run(args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, # Capture stderr as well for debugging
                                text=True)
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return -1, str(e)


def pick_audio(audio_dir):
    mp3_paths = []
    if not os.path.isdir(audio_dir):
        raise Exception(f"invalid audio_dir: {audio_dir}")
    for f in os.listdir(audio_dir):
        if f.endswith(".mp3"):
            mp3_paths.append(f"{audio_dir}/{f}")
    if len(mp3_paths) == 0:
        raise Exception(f"no mp3 file found in {audio_dir}")
    return random.choice(mp3_paths)


def parse_exif(exif_str):
    lines = exif_str.splitlines()
    iso = None
    fv = None
    focal_len = None
    exp_time = None
    len_model = None
    date_time_str = None
    for line in lines:
        if line.startswith("exif:FocalLength="):
            focal_len = int(eval(line.split("=")[-1]))
            print(f"focal_len: {focal_len}")
            continue
        if line.startswith("exif:PhotographicSensitivity="):
            iso = line.split("=")[-1]
            continue
        if line.startswith("exif:FNumber="):
            fv = eval(line.split("=")[-1])
            continue
        if line.startswith("exif:LensModel="):
            len_model = line.split("=")[-1]
        if line.startswith("exif:DateTimeOriginal="):
            date_time_str = line.split("=")[-1]
            len_model = line.split("=")[-1]
        if line.startswith("exif:ExposureTime="):
            exp_time = line.split("=")[-1]
            continue
    label = f"ISO {iso} {focal_len}mm f/{fv} {exp_time} sec           {len_model}                  {date_time_str}"
    return label


def get_exif_label(photo_path):
    cmd = f"identify -format '%[EXIF:*]' \"{photo_path}\""
    retcode, exif_str = run_os_command(cmd)
    exif_label = ""
    if retcode == 0:
        exif_label = parse_exif(exif_str)
    return exif_label

def get_photo_resolution(photo_path):
    cmd = f"convert \"{photo_path}\" -print '%w:%h' /dev/null"
    retcode, ret_str = run_os_command(cmd)
    if retcode == 0:
        # Output might contain other info, split by whitespace first if needed, 
        # but here we expect just resolution or error. 
        # On some systems convert might output warnings to stdout/stderr.
        # We try to find the w:h pattern.
        lines = ret_str.strip().splitlines()
        if lines:
            # simple attempt to grab the last line or the one looking like w:h
            last_line = lines[-1] 
            if ':' in last_line:
                 width,height = last_line.split(':')
                 return width,height
        return "0","0" # Fallback
    else:
        raise Exception(f"Failed to get resolution for {photo_path}, error: {ret_str}")
#

def add_meta(photo_path, new_photo_path):
    label = get_exif_label(photo_path)
    _, height = get_photo_resolution(photo_path)
    y_offset = int(0.47 * int(height))
    point_size = int(y_offset / 30)
    # Use single quotes for the label text to avoid shell expansion issues
    cmd = f"""convert \"{photo_path}\" -font helvetica -fill white -pointsize {point_size} -gravity center -draw "text 0,{y_offset} '{label}'" \"{new_photo_path}\""""
    print(cmd)
    run_os_command(cmd)


def get_video_duration(video_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
    retcode, duration_str = run_os_command(cmd)
    if retcode == 0 and duration_str.strip():
        try:
            return float(duration_str.strip())
        except ValueError:
            print(f"Warning: Could not parse duration from ffprobe output: {duration_str}")
            return 0
    print(f"Warning: Failed to get duration for {video_path}")
    return 0


def attach_audio(video_path, audio_path, total_len):
    fade_out_start = total_len - FADE_OUT_LEN
    cmd_str = f"ffmpeg -i \"{video_path}\" -stream_loop -1 -i \"{audio_path}\" -c:v copy -map 0:v -map 1:a -c:a aac -ac 2 -af \"afade=t=out:st={fade_out_start}:d={FADE_OUT_LEN}\" -shortest -y \"{OUTPUT_AUDIO_MP4}\""
    ret_code, _ = run_os_command(cmd_str)
    if ret_code == 0:
        print(f"{OUTPUT_AUDIO_MP4} created")
    else:
        print(f"Failed to attach audio {audio_path} for {OUTPUT_MP4}")

def process_one_media(i, media_file, sandbox_dir):
    supported_image_exts = (".jpg", ".jpeg")
    segment_path = os.path.join(sandbox_dir, f"segment_{i:03d}.mp4")
    print(f"Processing {media_file} into {segment_path}...")

    if media_file.lower().endswith(supported_image_exts):
        labeled_image_path = os.path.join(sandbox_dir, f"labeled_{i:03d}.jpg")
        add_meta(media_file, labeled_image_path)
        cmd = f"ffmpeg -loop 1 -t {TIME_GAP} -i \"{labeled_image_path}\" -vf \"scale=7680:4320:force_original_aspect_ratio=decrease:eval=frame,pad=7680:4320:-1:-1:eval=frame\" -r 25 -c:v libx264 -pix_fmt yuv420p \"{segment_path}\""
        run_os_command(cmd)
    else: # It's a video
        cmd = f"ffmpeg -i \"{media_file}\" -vf \"scale=7680:4320:force_original_aspect_ratio=decrease:eval=frame,pad=7680:4320:-1:-1:eval=frame\" -r 25 -c:v libx264 -pix_fmt yuv420p -an \"{segment_path}\""
        run_os_command(cmd)
    return segment_path

def main():
    parser = argparse.ArgumentParser(description="Create a video slideshow from photos and videos.")
    parser.add_argument("media_dir", help="Directory containing media files")
    parser.add_argument("audio_dir", help="Directory containing audio files")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker threads for processing media")
    args = parser.parse_args()

    media_dir = args.media_dir
    audio_dir = args.audio_dir
    num_workers = args.workers

    sandbox_dir = f"{media_dir}/sandbox"
    # Replaced rm -rf with shutil.rmtree
    if os.path.exists(sandbox_dir):
        shutil.rmtree(sandbox_dir)
    os.mkdir(sandbox_dir)

    # Get and sort all media files
    media_files = []
    supported_image_exts = (".jpg", ".jpeg")
    supported_video_exts = (".mp4", ".mov")
    for f in sorted(os.listdir(media_dir)):
        if f.lower().endswith(supported_image_exts) or f.lower().endswith(supported_video_exts):
            media_files.append(os.path.join(media_dir, f))

    if not media_files:
        print("No supported image or video files found in the directory.")
        sys.exit(0)

    # Create video segments from each media file using multithreading
    segment_paths = [None] * len(media_files)
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_index = {
            executor.submit(process_one_media, i, media_file, sandbox_dir): i
            for i, media_file in enumerate(media_files)
        }
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                segment_path = future.result()
                segment_paths[index] = segment_path
            except Exception as e:
                print(f"Media file {media_files[index]} generated an exception: {e}")
                sys.exit(1)

    # Concatenate all segments
    concat_file_path = os.path.join(sandbox_dir, "concat_list.txt")
    with open(concat_file_path, "w") as f:
        for segment in segment_paths:
             if segment:
                f.write(f"file '{os.path.abspath(segment)}'\n")

    print("Concatenating video segments...")
    # Replaced rm -f with os.remove
    if os.path.exists(OUTPUT_MP4):
        os.remove(OUTPUT_MP4)
    
    concat_cmd = f"ffmpeg -f concat -safe 0 -i \"{concat_file_path}\" -c copy \"{OUTPUT_MP4}\""
    ret_code, output = run_os_command(concat_cmd)
    if ret_code != 0:
        print(f"Failed to concatenate videos. Error: {output}")
        sys.exit(1)

    # Attach audio
    final_video_duration = get_video_duration(OUTPUT_MP4)
    if final_video_duration > 0:
        print(f"Attaching audio... Final video duration: {final_video_duration}s")
        audio_path = pick_audio(audio_dir)
        attach_audio(OUTPUT_MP4, audio_path, final_video_duration)
    else:
        print("Could not determine final video duration. Skipping audio attachment.")


if __name__ == "__main__":
    main()

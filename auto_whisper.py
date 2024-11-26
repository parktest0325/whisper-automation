import os
import whisper
from pathlib import Path

# model = whisper.load_model("large-v3")

from transformers import pipeline

transcriber = pipeline(
  "automatic-speech-recognition", 
  model="jonatasgrosman/whisper-large-zh-cv11"
)

transcriber.model.config.forced_decoder_ids = (
  transcriber.tokenizer.get_decoder_prompt_ids(
    language="zh", 
    task="transcribe"
  )
)

def generate_subtitle(folder_path):
    output_path = f"{folder_path}/auto_whisper_output"

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isdir(file_path):
            generate_subtitle(file_path)
        else:
            if not os.path.isfile(file_path) or not file_name.lower().endswith(('.mp4', '.mp3', '.wav', '.m4a', '.flac', '.aac')):
                continue

            try:
                os.makedirs(output_path, exist_ok=True)
                print(f"Processing file: {file_name}")
                # result = model.transcribe(file_path, language="zh")
                result = transcriber(file_path)
                print(result)
                segments = result["segments"]
                # segments = merge_segments_by_time(result["segments"])  
                subtitle_file = Path(output_path) / f"{Path(file_name).stem}.srt"

                with open(subtitle_file, "w", encoding="utf-8") as f:
                    for i, segment in enumerate(segments):
                        start = format_time(segment["start"])
                        end = format_time(segment["end"])
                        text = segment["text"]

                        f.write(f"{i + 1}\n{start} --> {end}\n{text.strip()}\n\n")
                
                print(f"Subtitles saved to {subtitle_file}")

            except Exception as e:
                print(f"Error processing {file_name}: {e}")          

def merge_segments_by_time(segments, min_gap=2.0):
    merged_segments = []
    current_segment = segments[0]
    bef_text = ""

    for i in range(1, len(segments)):
        next_segment = segments[i]
        
        if next_segment["start"] - current_segment["start"] < min_gap:
            current_segment["end"] = next_segment["end"]
            if bef_text != next_segment["text"]:
                current_segment["text"] += " " + next_segment["text"]
            bef_text = next_segment["text"]
        else:
            merged_segments.append(current_segment)
            current_segment = next_segment

    # Add the last segment
    merged_segments.append(current_segment)
    return merged_segments




def format_time(seconds: float) -> str:
    """Convert seconds to SRT time format (hh:mm:ss,ms)."""
    millis = int((seconds % 1) * 1000)
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02}:{mins:02}:{secs:02},{millis:03}"


if __name__ == "__main__":
    target = r'D:\BaiduNetdiskDownload\test'
    generate_subtitle(target)
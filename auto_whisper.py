import os
import sys
# import whisper
from pathlib import Path

# model = whisper.load_model("large-v3")


# from pydub import AudioSegment
# from transformers import pipeline

# transcriber = pipeline(
#   "automatic-speech-recognition", 
#   model="jonatasgrosman/whisper-large-zh-cv11",
#   device="cuda"
# )

# transcriber.model.config.forced_decoder_ids = (
#   transcriber.tokenizer.get_decoder_prompt_ids(
#     language="zh", 
#     task="transcribe"
#   )
# )


# transcriber = pipeline(
#   "automatic-speech-recognition", 
#   model="BELLE-2/Belle-whisper-large-v3-turbo-zh"
# )

# transcriber.model.config.forced_decoder_ids = (
#   transcriber.tokenizer.get_decoder_prompt_ids(
#     language="zh", 
#     task="transcribe"
#   )
# )

from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="cuda", compute_type="float16")

def generate_subtitle(folder_path):
    output_path = f"{folder_path}/auto_whisper_output"

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isdir(file_path):
            generate_subtitle(file_path)
        else:
            if not os.path.isfile(file_path) or not file_name.lower().endswith(('.mp4')):
                continue

            try:
                os.makedirs(output_path, exist_ok=True)
                subtitle_file = Path(output_path) / f"{Path(file_name).stem}.srt"
                if os.path.isfile(f"{subtitle_file}"):
                    print(f"skip {file_name} file!")
                    continue

                print(f"Processing file: {file_name}")
                segments, info = model.transcribe(file_path, language="zh", beam_size=5)

                # 몇몇 ai 모델은 wav 파일만 지원함
                # audio = AudioSegment.from_file(file_path, format="mp4")
                # audio_path = f"{folder_path}/{Path(file_name).stem}.wav"
                # audio.export(audio_path, format="wav")
                # result = transcriber(audio_path, return_timestamps=True)
                # print(result)
                # segments = result["segments"]
                
                segments = merge_segments_by_time(list(segments))

                with open(subtitle_file, "w", encoding="utf-8") as f:
                    for i, segment in enumerate(segments):
                        # print(segment)
                        start = format_time(segment["start"])
                        end = format_time(segment["end"])
                        text = segment["text"]

                        f.write(f"{i + 1}\n{start} --> {end}\n{text.strip()}\n\n")
                
                print(f"Subtitles saved to {subtitle_file}")

            except Exception as e:
                print(f"Error processing {file_name}: {e}")          
                raise

# 튜플과 딕셔너리를 잘 구분해서 사용해야함. 딕셔너리로 통일하면 좋을 것 같다. 
# segment merge, to dict type
def merge_segments_by_time(segments, merge_gap=1.0):
    merged_segments = []
    current_segment = {
        "start": segments[0].start,
        "end": segments[0].end,
        "text": segments[0].text,
    }

    bef_text = current_segment["text"]
    bef_start = current_segment["start"]

    for i in range(1, len(segments)):
        next_segment = segments[i]
        
        if next_segment.start - bef_start <= merge_gap:
            current_segment["end"] = next_segment.end
            if bef_text != next_segment.text:
                current_segment["text"] += " " + next_segment.text
        else:
            merged_segments.append(current_segment)
            current_segment = {
                "start": next_segment.start,
                "end": next_segment.end,
                "text": next_segment.text,
            }
        bef_text = next_segment.text
        bef_start = next_segment.start

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
    if len(sys.argv) < 2:
        print("Usage: python script.py <target_path>")
        sys.exit(1)
    target = sys.argv[1]
    generate_subtitle(target)
import os
import sys
from pathlib import Path
import re
from dotenv import load_dotenv
from openai import OpenAI
import json

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)

SEGMENT_SEP = "!@#/!@#"

RETRY_MODEL = [
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-mini",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4.1",
]

def load_from_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)

    subtitles = []
    for match in matches:
        index = int(match.group(1))
        start_time = match.group(2)
        end_time = match.group(3)
        text = match.group(4).strip()
        subtitles.append({
            'index': index,
            'start_time': start_time,
            'end_time': end_time,
            'text': text
        })

    return subtitles

def save_to_srt(subtitles, output_path):
    with open(output_path, 'w', encoding='utf-8') as file:
        for subtitle in subtitles:
            # SRT 형식으로 작성
            file.write(f"{subtitle['index']}\n")
            file.write(f"{subtitle['start_time']} --> {subtitle['end_time']}\n")
            file.write(f"{subtitle['text']}\n\n")  # 텍스트 끝에 빈 줄 추가

def translate_text(texts, length, m="gpt-4.1"):
    try:
        response = client.chat.completions.create(
            # response_format={"type": "json_object"}
            messages= [
                {
                    "role": "system",
                    "content": (
                        "You are a professional subtitle translator translating Chinese to Korean. "
                        "Keep all technical terms such as Android, Windows, Frida, DLL, Hooking, Rooting, FART, and so on, in English or use proper Korean terminology without paraphrasing or guessing. "
                        "Translate each line accurately and do not merge or split sentences arbitrarily. "
                        "This is subtitle text for a lecture on Android security, reverse engineering, hacking, and tools like Frida and FART. "
                        "Maintain the same number of lines. Avoid any stylistic rewriting."
                    )
                },
                {
                    "role": "user",
                    "content": f"The following consists of {length} subtitle lines, separated by the special marker '{SEGMENT_SEP}'. Translate each part line by line, preserving the separator and sentence count."
                },
                # {
                #     "role": "user",
                #     "content": (f"Return **exactly {length} translated lines** as a JSON "
                #                 f'object like {{"lines":["...", "..."]}}. '
                #                 "Do NOT add extra keys, comments or line breaks.")
                # },
                {
                    "role": "user",
                    "content": texts
                },
            ],
            temperature=0.3,
            model=m,
        )
        return [s.strip() for s in response.choices[0].message.content.split(f"\n{SEGMENT_SEP}")]
        # data = json.loads(response.choices[0].message.content)
        # return [s.strip() for s in data["lines"]]
    except Exception as e:
        print(f"Error translating text: {texts[0]}\n{e}")
        raise
        # return text

# TODO: json으로 던져주고 json으로 응답받기
def translate_srt(src, dst, batch_size=10, context_size=2, max_retries=len(RETRY_MODEL)-1):
    subtitles = load_from_srt(src)
    translated_subtitles = []

    for i in range(0, len(subtitles), batch_size):
        start_idx = max(i - context_size, 0)
        end_idx = min(i + batch_size + context_size, len(subtitles))
        context_batch = subtitles[start_idx:end_idx]

        texts_to_translate = f"\n{SEGMENT_SEP}\n".join([elem['text'] for elem in context_batch]) #+ f"\n{SEGMENT_SEP}\n"
        # texts_to_translate = [elem['text'] for elem in context_batch]
        translated_batch = None

        # 우아한 재시도 로직
        for attempt in range(max_retries):
            try:
                translated_batch = translate_text(texts_to_translate, len(context_batch), RETRY_MODEL[attempt])

                # 번역한 라인의 갯수가 맞지 않는 경우.. (마음대로 병합해버릴 수 있으니)
                if len(context_batch) != len(translated_batch):
                    # print("hmm.. count is not match!! ->", i, len(context_batch), len(translated_batch) )
                    # print(context_batch)
                    # print(translated_batch)
                    # print(texts_to_translate)
                    raise ValueError(f"Line count mismatch: using {RETRY_MODEL[attempt]} Expected {len(context_batch)}, Got {len(translated_batch)}")
                # 성공 시 루프 break
                break
            except Exception as e:
                print(f"Retry {attempt + 1}/{max_retries} failed for batch {i}. Error: {e}")
                if attempt + 1 == max_retries:
                    raise RuntimeError(f"Failed after {max_retries} attempts for batch {i}") from e

        begin = 0 if i == 0 else context_size
        translated_current = translated_batch[begin : begin + batch_size]
        for j, elem in enumerate(subtitles[i:i + batch_size]):
            translated_subtitles.append({
                'index': elem['index'],
                'start_time': elem['start_time'],
                'end_time': elem['end_time'],
                'text': translated_current[j]
            })

    save_to_srt(translated_subtitles, dst)


def translate_subtitle(folder_path, path_ends):
    subtitle_folder = f"{folder_path}/{path_ends}"

    for file_name in os.listdir(folder_path):
        if file_name is path_ends:
            continue
        file_path = os.path.join(folder_path, file_name)

        if os.path.isdir(file_path):
            translate_subtitle(file_path, path_ends)
        else:
            if not os.path.isfile(file_path) or not file_name.lower().endswith(('.mp4')):
                continue
            try:

                org_subtitle_file = Path(subtitle_folder) / f"{Path(file_name).stem}.srt"
                if os.path.isfile(f"{org_subtitle_file}_done"):
                    print(f"skip {file_path} file!")
                    continue

                translated_name = re.sub(r'[\/:*?"<>|]', '',translate_text(file_name, 1, "gpt-4.1")[0].replace(' ',''))
                print(f"Processing file: {file_path} -> {translated_name}")

                translated_subtitle_file = Path(subtitle_folder) / f"{Path(translated_name).stem}.srt"
                translate_srt(org_subtitle_file, translated_subtitle_file)

                renamed_file = f"{folder_path}/{translated_name}"
                os.rename(file_path, renamed_file)
                # 완료된 파일 체크
                Path(f"{translated_subtitle_file}_done").touch(exist_ok=True) 

            except Exception as e:
                print(f"Error processing {file_name}: {e}")          
                raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <target_path>")
        sys.exit(1)
    target = sys.argv[1]
    path_ends = r'auto_whisper_output'
    translate_subtitle(target, path_ends)
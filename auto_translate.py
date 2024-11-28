import os
from pathlib import Path
import re
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)


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

def translate_text(texts, length):
    try:
        print(texts)
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "The following text needs to be translated from Chinese to Korean. Do not change the English words in the sentence to Korean."
                },
                {
                    "role": "system",
                    "content": f"It consists of a total of {length} sentences, each separated by a newline. Please translate all sentences accurately and do not combine lines arbitrarily."
                },
                {
                    "role": "system",
                    "content": "This text is part of subtitles for a lecture on gaming, hacking, security, Android, and Windows. Technical terms (e.g., Android, Windows, DLL, Malware) should be written in English or translated into appropriate Korean expressions where necessary."
                },
                {"role": "user", "content": texts}
            ],
            model="gpt-4o",  # 사용 모델
            max_tokens=5000
        )
        print(response)
        return response.choices[0].message.content.split('\n\n')
    except Exception as e:
        print(f"Error translating text: {texts[0]}\n{e}")
        raise
        # return text


def translate_srt(src, dst, batch_size=10, context_size=2):
    subtitles = load_from_srt(src)
    print
    translated_subtitles = []

    for i in range(0, len(subtitles), batch_size):
        start_idx = max(i - context_size, 0)
        end_idx = min(i + batch_size + context_size, len(subtitles))
        context_batch = subtitles[start_idx:end_idx]

        texts_to_translate = "\n\n".join([elem['text'] for elem in context_batch])
        translated_batch = translate_text(texts_to_translate, len(context_batch))

        # 번역 결과에서 현재 묶음만 저장
        translated_current = translated_batch[context_size:context_size + batch_size]
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
                translated_name = translate_text(file_name, 1)[0].replace(' ','')
                os.rename(file_path, f"{folder_path}/{translated_name}")

                org_subtitle_file = Path(subtitle_folder) / f"{Path(file_name).stem}.srt"
                translated_subtitle_file = Path(subtitle_folder) / f"{Path(translated_name).stem}.srt"
                translate_srt(org_subtitle_file, translated_subtitle_file)

            except Exception as e:
                print(f"Error processing {file_name}: {e}")          
                raise


if __name__ == "__main__":
    target = r'D:\BaiduNetdiskDownload\test'
    path_ends = r'auto_whisper_output'
    translate_subtitle(target, path_ends)
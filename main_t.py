import re
import MeCab
import cv2
import numpy as np
from PIL import Image
from wordcloud import WordCloud


def process(input_file_name, output_file_name):
    # -----------------------------
    # パラメータ設定
    # -----------------------------
    temp_file = "temp.png"        # 一時保存用ファイル

    # 不要なキーワードリスト（小文字・大文字の区別など、場合に応じて工夫してください）
    keywords_to_remove = {
        "例",  # 例としていくつか入れています
        "こと",
        "する",
        "ある",
        "いる",
        "これ",
        "ため",
        "場合",
    }

    # 幅・高さを WordCloud の width, height に合わせる
    width, height = 800, 600

    # 楕円マスク用の配列（真っ黒=0 で初期化）
    ellipse_mask = np.zeros((height, width), dtype=np.uint8)

    # (width//2, height//2)を中心に、(width//2, height//2)の長軸・短軸を持つ楕円を真っ白=255で塗り潰し
    cv2.ellipse(
        ellipse_mask,
        center=(width // 2, height // 2),
        axes=(width // 2, height // 2),
        angle=0,
        startAngle=0,
        endAngle=360,
        color=255,
        thickness=-1
    )

    ellipse_mask = 255 - ellipse_mask

    # WordCloud 用設定（必要に応じて修正）
    wc_config = {
        "width": width,
        "height": height,
        "max_words": 100,
        "background_color": "white",
        "font_path": "/System/Library/Fonts/Helvetica.ttc",
        "mask": ellipse_mask,
        "colormap": 'ocean',
    }

    # -----------------------------
    # テキストファイルの読み込み
    # -----------------------------
    with open(input_file_name, encoding="utf-8") as f:
        lines = f.readlines()

    processed_lines = []
    for line in lines:
        # 先頭が "@" の行は無視
        if line.startswith("@"):
            continue

        # 不要な LaTeX 部分を除去
        line = re.sub(r'\\cite\{.*?\}', '', line)         # \cite{...}
        line = re.sub(r'\\ref\{.*?\}', '', line)          # \ref{...}
        line = re.sub(r'\$\$.*?\$\$', '', line, flags=re.DOTALL)  # $$...$$
        
        # （）内の文字を除去
        line = re.sub(r'（.*?）', '', line)

        # 文字列の前後の空白を除去
        line = line.strip()

        if line:
            processed_lines.append(line)

    # -----------------------------
    # MeCab による名詞抽出とひらがな変換
    # -----------------------------
    tagger = MeCab.Tagger('-d /opt/homebrew/lib/mecab/dic/ipadic')
    nouns = []
    hiragana_text = ""

    for text_line in processed_lines:
        node = tagger.parseToNode(text_line)
        while node:
            # 品詞情報は feature に含まれ、カンマ区切りで格納されることが多いです。
            # 例: "名詞,一般,*,*,*,*,Python,パイソン,パイソン"
            features = node.feature.split(",")
            if features[0] == "名詞":
                surface = node.surface
                # 不要なキーワードを除外
                if surface not in keywords_to_remove:
                    nouns.append(surface)

            # 読み情報を取得してひらがなに変換
            if len(features) >= 8 and features[7] != '*':
                reading = features[7]
                print(reading)
                # カタカナをひらがなに変換
                hiragana_reading = ""
                for char in reading:
                    if 'ア' <= char <= 'ン':
                        hiragana_reading += chr(ord(char) - ord('ア') + ord('あ'))
                    else:
                        hiragana_reading += char
                hiragana_text += hiragana_reading
            else:
                # 読み情報がない場合は元の文字をそのまま使用
                hiragana_text += node.surface

            node = node.next

    # ひらがなとカタカナと長音符の文字数をカウント
    hiragana_count = 0
    for char in hiragana_text:
        if 'あ' <= char <= 'ん' or 'ア' <= char <= 'ン' or char == 'ー':
            hiragana_count += 1

    # 最終的に名詞のみ連結した文字列をワードクラウドに渡す
    text_for_wordcloud = " ".join(nouns)

    print(text_for_wordcloud)
    print(f"{len(nouns)} words")
    print(f"ひらがな・カタカナ文字数: {hiragana_count}")

    # -----------------------------
    # WordCloud を生成
    # -----------------------------
    wordcloud = WordCloud(**wc_config).generate(text_for_wordcloud)

    # WordCloud の出力を一時ファイル(temp.png)に保存 (PIL 形式)
    wordcloud.to_file(temp_file)

    # -----------------------------
    # OpenCV で読み込んで a.png に保存
    # -----------------------------
    # temp.png を OpenCV 形式で読み込む
    img_cv2 = cv2.imread(temp_file)

    # a.png に書き出す
    cv2.imwrite(output_file_name, img_cv2)


if __name__ == "__main__":
    input_file_name = "abstract.txt"
    output_file_name = "abstract.png"

    process(input_file_name, output_file_name)

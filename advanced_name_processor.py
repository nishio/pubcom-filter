
import neologdn
import csv
import argparse
import re
from collections import defaultdict
import unicodedata
import difflib

def normalize_text(text, remove_symbols=True, normalize_numbers=True):
    """neologdnを使ってテキストを正規化する"""
    if not text or not isinstance(text, str):
        return ""
        
    normalized = neologdn.normalize(text)
    
    normalized = normalized.lower()
    
    normalized = unicodedata.normalize('NFKC', normalized)
    
    if remove_symbols:
        normalized = re.sub(r'[「」『』（）\(\)\[\]\{\}【】、。,\.・:：;；!！?？\-_=+~～@#$%^&*]', '', normalized)
    
    if normalize_numbers:
        normalized = re.sub(r'\d+', '0', normalized)
    
    return normalized

def calculate_similarity(text1, text2):
    """2つのテキスト間の類似度を計算する"""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def group_similar_texts(texts, similarity_threshold=0.8):
    """類似度に基づいてテキストをグループ化する"""
    groups = []
    processed = set()
    
    for i, (id1, text1) in enumerate(texts):
        if id1 in processed:
            continue
            
        current_group = [(id1, text1)]
        processed.add(id1)
        
        for j, (id2, text2) in enumerate(texts):
            if id2 in processed or i == j:
                continue
                
            norm_text1 = normalize_text(text1)
            norm_text2 = normalize_text(text2)
            
            if norm_text1 == norm_text2 or calculate_similarity(norm_text1, norm_text2) >= similarity_threshold:
                current_group.append((id2, text2))
                processed.add(id2)
        
        groups.append(current_group)
    
    return groups

def process_file(input_file, output_file, similarity_threshold=0.8, id_col=0, text_col=1):
    """ファイルを処理して類似テキストをグループ化する"""
    texts = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダーをスキップ
        
        for row in reader:
            if len(row) <= max(id_col, text_col):
                continue
                
            id_value = row[id_col]
            text = row[text_col]
            
            texts.append((id_value, text))
    
    groups = group_similar_texts(texts, similarity_threshold)
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['group_id', 'count', 'representative_text', 'normalized_text', 'ids', 'original_texts'])
        
        for group_id, group in enumerate(groups):
            if not group:
                continue
                
            representative_text = group[0][1]
            
            normalized_text = normalize_text(representative_text)
            
            ids = [item[0] for item in group]
            original_texts = [item[1] for item in group]
            
            writer.writerow([
                group_id,
                len(group),
                representative_text,
                normalized_text,
                '|'.join(ids),
                '|'.join(original_texts)
            ])

def main():
    parser = argparse.ArgumentParser(description='類似テキストをグループ化するツール')
    parser.add_argument('input_file', help='入力CSVファイルのパス')
    parser.add_argument('output_file', help='出力CSVファイルのパス')
    parser.add_argument('--similarity', type=float, default=0.8, help='類似度のしきい値（0.0〜1.0）')
    parser.add_argument('--id-col', type=int, default=0, help='IDの列番号（0始まり）')
    parser.add_argument('--text-col', type=int, default=1, help='テキストの列番号（0始まり）')
    
    args = parser.parse_args()
    
    process_file(args.input_file, args.output_file, args.similarity, args.id_col, args.text_col)
    print(f"処理が完了しました。結果は{args.output_file}に保存されています。")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("サンプルデータを使用します...")
        
        sample_data = [
            ['id', 'text'],
            ['1', '山田太郎'],
            ['2', 'ヤマダタロウ'],
            ['3', '山田　太郎'],
            ['4', '山田太郎さん'],
            ['5', '鈴木一郎'],
            ['6', 'スズキイチロウ'],
            ['7', '鈴木　一郎'],
            ['8', '山田太郎（30歳）'],
            ['9', '山田太郎30歳'],
            ['10', '山田 太郎（会社員）'],
            ['11', '全く同じ意見です。賛成します。'],
            ['12', '全く同じ意見です！賛成します！'],
            ['13', '全く同じ意見。賛成。'],
            ['14', '意見が全く同じです。賛成します。'],
        ]
        
        with open('sample_input.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(sample_data)
        
        process_file('sample_input.csv', 'grouped_texts.csv')
        
        print("サンプル処理が完了しました。結果はgrouped_texts.csvに保存されています。")
        
        with open('grouped_texts.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                print(row)
    else:
        main()

import neologdn
import csv
import argparse
import re
from collections import defaultdict
import unicodedata
import difflib
import time
from tqdm import tqdm

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

def process_file(input_file, output_file, similarity_threshold=0.8, id_col=0, text_col=1):
    """ファイルを処理して類似テキストをグループ化する（最適化版）"""
    print("テキストの読み込みと正規化を開始...")
    texts = []
    normalized_texts = {}
    
    # 1. 全テキストを読み込み、正規化する
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダーをスキップ
        
        for row in reader:
            if len(row) <= max(id_col, text_col):
                continue
                
            id_value = row[id_col]
            text = row[text_col]
            
            texts.append((id_value, text))
            normalized_texts[id_value] = normalize_text(text)
    
    print(f"読み込み完了: {len(texts)}件のテキスト")
    
    # 2. 完全一致するテキストをグループ化
    print("完全一致するテキストのグループ化...")
    exact_match_groups = defaultdict(list)
    processed_ids = set()
    
    for id_value, text in texts:
        norm_text = normalized_texts[id_value]
        if not norm_text:  # 空のテキストはスキップ
            continue
        exact_match_groups[norm_text].append((id_value, text))
        processed_ids.add(id_value)
    
    # 3. 類似テキストをグループ化（完全一致しないもののみ）
    print("類似テキストのグループ化...")
    similarity_groups = []
    
    # 完全一致グループから代表テキストを1つずつ取り出す
    unique_norm_texts = list(exact_match_groups.keys())
    
    # 類似度に基づいてグループ化
    remaining_texts = []
    for i, norm_text in enumerate(unique_norm_texts):
        if i % 100 == 0:
            print(f"処理中... {i}/{len(unique_norm_texts)}")
        
        # このグループの代表テキスト
        group = exact_match_groups[norm_text]
        representative = group[0]
        
        # 既に類似グループに入っているかチェック
        skip = False
        for existing_group in similarity_groups:
            rep_norm = normalized_texts[existing_group[0][0]]
            if calculate_similarity(norm_text, rep_norm) >= similarity_threshold:
                existing_group.extend(group)
                skip = True
                break
        
        if not skip:
            remaining_texts.append((representative, norm_text, group))
    
    # 残りのテキストを類似度でグループ化
    for i, (rep, norm_text, group) in enumerate(remaining_texts):
        if i % 100 == 0:
            print(f"最終グループ化... {i}/{len(remaining_texts)}")
        
        # 既に処理済みならスキップ
        if rep[0] in processed_ids:
            continue
        
        current_group = group
        processed_ids.update([item[0] for item in group])
        
        for j, (other_rep, other_norm, other_group) in enumerate(remaining_texts):
            if i == j or other_rep[0] in processed_ids:
                continue
            
            if calculate_similarity(norm_text, other_norm) >= similarity_threshold:
                current_group.extend(other_group)
                processed_ids.update([item[0] for item in other_group])
        
        similarity_groups.append(current_group)
    
    # 4. 結果を出力
    print("結果の出力...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['group_id', 'match_type', 'count', 'representative_text', 'normalized_text', 'ids', 'original_texts'])
        
        # 完全一致グループの出力
        for group_id, (norm_text, group) in enumerate(exact_match_groups.items()):
            if len(group) <= 1:  # 1件のみのグループはスキップ
                continue
                
            representative_text = group[0][1]
            ids = [item[0] for item in group]
            original_texts = [item[1] for item in group]
            
            writer.writerow([
                f"exact_{group_id}",
                "exact",
                len(group),
                representative_text,
                norm_text,
                '|'.join(ids),
                '|'.join(original_texts)
            ])
        
        # 類似グループの出力
        for group_id, group in enumerate(similarity_groups):
            if len(group) <= 1:  # 1件のみのグループはスキップ
                continue
                
            representative_text = group[0][1]
            normalized_text = normalized_texts[group[0][0]]
            
            ids = [item[0] for item in group]
            original_texts = [item[1] for item in group]
            
            writer.writerow([
                f"similar_{group_id}",
                "similar",
                len(group),
                representative_text,
                normalized_text,
                '|'.join(ids),
                '|'.join(original_texts)
            ])
    
    # 5. 統計情報
    exact_match_count = sum(1 for group in exact_match_groups.values() if len(group) > 1)
    similar_match_count = len(similarity_groups)
    total_exact_items = sum(len(group) for group in exact_match_groups.values() if len(group) > 1)
    total_similar_items = sum(len(group) for group in similarity_groups)
    
    stats = {
        "total_items": len(texts),
        "exact_match_groups": exact_match_count,
        "similar_match_groups": similar_match_count,
        "total_exact_items": total_exact_items,
        "total_similar_items": total_similar_items
    }
    
    # 統計情報をJSONで保存
    import json
    with open(output_file + ".stats.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"処理が完了しました。結果は{output_file}に保存されています。")
    print(f"統計情報: 全{len(texts)}件中、完全一致グループ{exact_match_count}件（{total_exact_items}アイテム）、類似グループ{similar_match_count}件（{total_similar_items}アイテム）")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='類似テキストをグループ化するツール（最適化版）')
    parser.add_argument('input_file', help='入力CSVファイルのパス')
    parser.add_argument('output_file', help='出力CSVファイルのパス')
    parser.add_argument('--similarity', type=float, default=0.8, help='類似度のしきい値（0.0〜1.0）')
    parser.add_argument('--id-col', type=int, default=0, help='IDの列番号（0始まり）')
    parser.add_argument('--text-col', type=int, default=1, help='テキストの列番号（0始まり）')
    
    args = parser.parse_args()
    
    start_time = time.time()
    stats = process_file(args.input_file, args.output_file, args.similarity, args.id_col, args.text_col)
    end_time = time.time()
    
    print(f"処理時間: {end_time - start_time:.2f}秒")
    return stats

if __name__ == "__main__":
    try:
        import tqdm
    except ImportError:
        print("tqdmをインストールしています...")
        import subprocess
        subprocess.check_call(["pip", "install", "tqdm"])
    
    main()

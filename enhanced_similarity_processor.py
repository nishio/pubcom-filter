import neologdn
import csv
import argparse
import re
from collections import defaultdict, Counter
import unicodedata
import difflib
import time
import json
from janome.tokenizer import Tokenizer
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

tokenizer = Tokenizer()

def morphological_analysis(text):
    """形態素解析を行い、名詞と動詞の原形のみを抽出する"""
    if not text or not isinstance(text, str):
        return ""
    
    tokens = tokenizer.tokenize(text)
    
    functional_words = []
    for token in tokens:
        pos = token.part_of_speech.split(',')[0]  # 品詞の最初の要素
        
        if pos == '名詞':
            functional_words.append(token.surface)
        
        elif pos == '動詞':
            base_form = token.base_form
            functional_words.append(base_form)
    
    return ' '.join(functional_words)

def calculate_word_similarity(text1, text2):
    """単語の重複に基づく類似度を計算する（拡張Jaccard係数）"""
    if not text1 or not text2:
        return 0.0
    
    words1 = text1.split()
    words2 = text2.split()
    
    counter1 = Counter(words1)
    counter2 = Counter(words2)
    
    common_weight = sum(min(counter1[word], counter2[word]) for word in set(counter1).intersection(set(counter2)))
    
    total_weight = sum(counter1.values()) + sum(counter2.values()) - common_weight
    
    if total_weight == 0:
        return 0.0
    
    min_length = min(len(words1), len(words2))
    max_length = max(len(words1), len(words2))
    length_ratio = min_length / max_length if max_length > 0 else 0
    
    base_similarity = common_weight / total_weight
    
    adjusted_similarity = base_similarity * (1 + length_ratio) / 2
    
    return adjusted_similarity

def process_file(input_file, output_file, similarity_threshold=0.2, id_col=0, text_col=1, sample_size=None):
    """ファイルを処理して類似テキストをグループ化する（拡張類似度版）"""
    print("テキストの読み込みを開始...")
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
            
            if sample_size and len(texts) >= sample_size:
                break
    
    print(f"読み込み完了: {len(texts)}件のテキスト")
    
    print("テキストの正規化と形態素解析を開始...")
    normalized_texts = {}
    morphological_texts = {}
    
    for id_value, text in tqdm.tqdm(texts, desc="テキスト処理"):
        normalized_texts[id_value] = normalize_text(text)
        morphological_texts[id_value] = morphological_analysis(text)
    
    print("形態素解析に基づく完全一致テキストのグループ化...")
    exact_match_groups = defaultdict(list)
    processed_ids = set()
    
    for id_value, text in texts:
        morph_text = morphological_texts[id_value]
        if not morph_text:  # 空のテキストはスキップ
            continue
        exact_match_groups[morph_text].append((id_value, text))
        processed_ids.add(id_value)
    
    print("形態素解析に基づく類似テキストのグループ化（拡張類似度）...")
    similarity_groups = []
    
    unique_morph_texts = list(exact_match_groups.keys())
    
    remaining_texts = []
    for morph_text in tqdm.tqdm(unique_morph_texts, desc="代表テキスト処理"):
        group = exact_match_groups[morph_text]
        representative = group[0]
        
        skip = False
        for existing_group in similarity_groups:
            rep_morph = morphological_texts[existing_group[0][0]]
            if calculate_word_similarity(morph_text, rep_morph) >= similarity_threshold:
                existing_group.extend(group)
                skip = True
                break
        
        if not skip:
            remaining_texts.append((representative, morph_text, group))
    
    for i, (rep, morph_text, group) in enumerate(tqdm.tqdm(remaining_texts, desc="類似グループ化")):
        if rep[0] in processed_ids and i > 0:
            continue
        
        current_group = group.copy()
        processed_ids.update([item[0] for item in group])
        
        for j, (other_rep, other_morph, other_group) in enumerate(remaining_texts):
            if i == j or other_rep[0] in processed_ids:
                continue
            
            similarity = calculate_word_similarity(morph_text, other_morph)
            if similarity >= similarity_threshold:
                current_group.extend(other_group)
                processed_ids.update([item[0] for item in other_group])
        
        if len(current_group) > 1:  # 1件のみのグループは追加しない
            similarity_groups.append(current_group)
    
    print("結果の出力...")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['group_id', 'match_type', 'count', 'representative_text', 'morphological_text', 'similarity_score', 'ids', 'original_texts'])
        
        for group_id, (morph_text, group) in enumerate(exact_match_groups.items()):
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
                morph_text,
                "1.0",  # 完全一致の類似度は1.0
                '|'.join(ids),
                '|'.join(original_texts)
            ])
        
        for group_id, group in enumerate(similarity_groups):
            if len(group) <= 1:  # 1件のみのグループはスキップ
                continue
                
            representative_text = group[0][1]
            morphological_text = morphological_texts[group[0][0]]
            
            similarity_scores = []
            for item in group[1:]:  # 代表テキスト以外のアイテム
                item_morph = morphological_texts[item[0]]
                score = calculate_word_similarity(morphological_text, item_morph)
                similarity_scores.append(score)
            
            avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
            
            ids = [item[0] for item in group]
            original_texts = [item[1] for item in group]
            
            writer.writerow([
                f"similar_{group_id}",
                "similar",
                len(group),
                representative_text,
                morphological_text,
                f"{avg_similarity:.4f}",
                '|'.join(ids),
                '|'.join(original_texts)
            ])
    
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
    
    with open(output_file + ".stats.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"処理が完了しました。結果は{output_file}に保存されています。")
    print(f"統計情報: 全{len(texts)}件中、形態素解析による完全一致グループ{exact_match_count}件（{total_exact_items}アイテム）、類似グループ{similar_match_count}件（{total_similar_items}アイテム）")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='形態素解析と拡張類似度を用いた類似テキストグループ化ツール')
    parser.add_argument('input_file', help='入力CSVファイルのパス')
    parser.add_argument('output_file', help='出力CSVファイルのパス')
    parser.add_argument('--similarity', type=float, default=0.2, help='類似度のしきい値（0.0〜1.0）')
    parser.add_argument('--id-col', type=int, default=0, help='IDの列番号（0始まり）')
    parser.add_argument('--text-col', type=int, default=1, help='テキストの列番号（0始まり）')
    parser.add_argument('--sample', type=int, default=None, help='処理するサンプル数（指定しない場合は全件処理）')
    
    args = parser.parse_args()
    
    start_time = time.time()
    stats = process_file(args.input_file, args.output_file, args.similarity, args.id_col, args.text_col, args.sample)
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
    
    try:
        import janome
    except ImportError:
        print("janomeをインストールしています...")
        import subprocess
        subprocess.check_call(["pip", "install", "janome"])
    
    main()

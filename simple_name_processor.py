
import neologdn
import csv
from collections import defaultdict

def normalize_text(text):
    """neologdnを使ってテキストを正規化する"""
    normalized = neologdn.normalize(text)
    normalized = normalized.lower()
    return normalized

def process_names(input_file, output_file):
    """類似した名前をグループ化する"""
    name_groups = defaultdict(list)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # ヘッダーをスキップ
        
        for row in reader:
            if len(row) < 2:  # 最低限IDとテキストが必要
                continue
                
            id_value = row[0]
            text = row[1]
            
            normalized_text = normalize_text(text)
            
            name_groups[normalized_text].append((id_value, text))
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['group_id', 'normalized_text', 'count', 'original_texts'])
        
        for group_id, (normalized_text, items) in enumerate(name_groups.items()):
            original_texts = [item[1] for item in items]
            writer.writerow([
                group_id,
                normalized_text,
                len(items),
                '|'.join(original_texts)
            ])

if __name__ == "__main__":
    sample_data = [
        ['id', 'text'],
        ['1', '山田太郎'],
        ['2', 'ヤマダタロウ'],
        ['3', '山田　太郎'],
        ['4', '山田太郎さん'],
        ['5', '鈴木一郎'],
        ['6', 'スズキイチロウ'],
        ['7', '鈴木　一郎'],
    ]
    
    with open('sample_input.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(sample_data)
    
    process_names('sample_input.csv', 'grouped_names.csv')
    
    print("処理が完了しました。結果はgrouped_names.csvに保存されています。")
    
    with open('grouped_names.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            print(row)

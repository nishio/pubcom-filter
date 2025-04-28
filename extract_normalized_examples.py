import csv
import json
import os

def extract_normalized_examples(input_file, output_file, max_examples=10):
    """
    Extract examples of comments that weren't identical but became the same after neologdn normalization.
    
    Args:
        input_file: Path to the input CSV file with grouped comments
        output_file: Path to the output markdown file
        max_examples: Maximum number of examples to extract
    """
    examples = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        
        for row in reader:
            if len(row) < 7 or row[1] != 'exact':
                continue
                
            original_texts = row[6].split('|')
            if len(original_texts) <= 1:
                continue
                
            first_text = original_texts[0]
            different_texts = []
            
            for text in original_texts[1:]:
                if text != first_text:
                    different_texts.append(text)
                    
            if different_texts:
                example = {
                    'group_id': row[0],
                    'count': len(original_texts),
                    'representative_text': row[3],
                    'first_text': first_text,
                    'different_texts': different_texts[:3]  # Limit to 3 different texts
                }
                examples.append(example)
                
            if len(examples) >= max_examples:
                break
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('# neologdnによる正規化で同一視された例\n\n')
        f.write('元のテキストが異なるが、正規化後に同一と判定された例を表示します。\n\n')
        
        if not examples:
            f.write('元のテキストが異なるが正規化後に同一と判定された例は見つかりませんでした。\n')
            return
        
        for i, example in enumerate(examples):
            f.write(f'## グループ {example["group_id"]} ({example["count"]}件)\n\n')
            f.write('代表テキスト:\n')
            f.write(f'```\n{example["representative_text"]}\n```\n\n')
            f.write('元のテキスト（違いがある例）:\n\n')
            
            f.write('テキスト1:\n')
            f.write(f'```\n{example["first_text"]}\n```\n\n')
            
            for j, text in enumerate(example["different_texts"]):
                f.write(f'テキスト{j+2}:\n')
                f.write(f'```\n{text}\n```\n\n')
            
            f.write('---\n\n')
    
    print(f'Extracted {len(examples)} examples to {output_file}')

def main():
    result_files = [
        'grouped_full_comments.csv',
        'grouped_full_comments_0.7.csv',
        'grouped_full_comments_0.5.csv',
        'exact_matches_sorted.csv'
    ]
    
    for file in result_files:
        if os.path.exists(file):
            output_file = 'neologdn_normalized_examples.md'
            extract_normalized_examples(file, output_file)
            return
    
    print('No result files found. Please run the analysis first.')

if __name__ == '__main__':
    main()

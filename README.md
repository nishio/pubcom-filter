# pubcom-filter

neologdnを使用して日本語テキストの類似性を検出し、類似した投稿をグループ化するツールです。

## ファイル説明

- `simple_name_processor.py`: 基本的な名前処理ツール
- `advanced_name_processor.py`: より高度なテキスト類似性検出ツール

## 使用方法

### 基本的な名前処理ツール

```bash
python simple_name_processor.py
```

このスクリプトは、サンプルデータを使用して名前の正規化とグループ化を行います。

### 高度なテキスト類似性検出ツール

```bash
python advanced_name_processor.py [入力ファイル] [出力ファイル] [オプション]
```

#### オプション

- `--similarity`: 類似度のしきい値（0.0〜1.0、デフォルト: 0.8）
- `--id-col`: IDの列番号（0始まり、デフォルト: 0）
- `--text-col`: テキストの列番号（0始まり、デフォルト: 1）

#### 例

```bash
python advanced_name_processor.py input.csv output.csv --similarity 0.7 --id-col 0 --text-col 1
```

引数なしで実行すると、サンプルデータを使用してデモを実行します。

## 機能

1. **テキスト正規化**: neologdnを使用して日本語テキストを正規化
2. **類似テキストのグループ化**: 正規化されたテキストと類似度計算に基づいてグループ化
3. **柔軟な類似度設定**: 類似度のしきい値を調整可能
4. **CSVファイル対応**: 入出力にCSVファイルを使用

## 依存パッケージ

- neologdn: 日本語テキスト正規化ライブラリ

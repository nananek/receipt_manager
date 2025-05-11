# Receipt Manager

Flask + OpenAI Vision を用いた日本語レシート解析・CSVエクスポートアプリケーション。

- レシート画像から「日付・時刻・店名・金額・決済手段」を抽出
- GnuCash等にインポート可能なCSV形式で出力
- 手動登録・編集にも対応
- PWA対応（スマートフォンホーム画面から起動可能）

---

## ✅ 必要条件

- Python 3.11+
- Docker（推奨） / またはローカル環境に `pip install -r requirements.txt`
- OpenAI API Key（`.env` に指定）

---

## 📦 インストール手順

### Docker を使う場合（推奨）

```bash
cp .env.sample .env
# .env を編集し、以下を設定してください：
# SQLALCHEMY_DATABASE_URI=sqlite:////app/instance/receipts.db
# OPENAI_API_KEY=sk-...

docker-compose -f docker-compose.yml.sample up --build
```

ブラウザで http://localhost:5000 を開いてください。

---

### ローカル環境で直接実行する場合（Python仮想環境など）

```bash
cp .env.sample .env
# .env を編集

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python app.py
```

---

## 🔄 データベースのマイグレーション（アップデート時）

DBスキーマに変更があった場合は以下を実行してください：

```bash
# 1. .env に SQLALCHEMY_DATABASE_URI を設定
# 2. マイグレーションを反映
alembic upgrade head
```

新しいモデル追加時のマイグレーション生成例：

```bash
alembic revision --autogenerate -m "add new column to Receipt"
```

---

## 🗃️ 出力CSV形式

出力されるCSVは以下の形式です：

```
日付,店名,金額
2025-05-11,セブンイレブン,1200
```

文字コードは `CP932`（Windows対応）です。

---

## 🛡️ セキュリティ

- `.env` には機密情報（APIキーなど）を含むため **絶対にGit管理しないでください**
- `.gitignore` に `.env`, `instance/*.db`, `uploads/` などを含めています

---

## 📄 ライセンス

MIT License

(c) 2025 Nekono Nana KAKKO KARI

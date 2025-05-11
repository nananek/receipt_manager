FROM python:3.11-slim

# 作業ディレクトリ設定
WORKDIR /app

# 必要なパッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコード
COPY . .

# ポート開放
EXPOSE 5000

# 起動コマンド
CMD ["python", "app.py"]

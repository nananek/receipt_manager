#!/usr/bin/env python3.11
import base64
import os
from PIL import Image
from io import BytesIO
from openai import OpenAI
import json

def analyze_receipt_image(image: Image.Image, prompt_appendix: str = "") -> dict:
  # OpenAIクライアント初期化
  client = OpenAI()
  """
  レシート画像（PIL.Image）を受け取り、整形されたレシート情報をdictで返す。
  OpenAI GPT-4o を使用。
  """
  # 画像をBase64に変換
  buffered = BytesIO()
  format = image.format or "JPEG"
  image.save(buffered, format=format)
  mime_type = f"image/{format.lower()}"
  base64_image = base64.b64encode(buffered.getvalue()).decode()

  # プロンプト定義
  prompt_text = """
次のレシート画像を解析し、以下のJSON構造で出力してください：

- 日本のレシートには、複数の税区分が含まれる場合があります。
- 税区分には次の3つがあります：
  1. 標準税率（10%）：主に飲食料品以外
  2. 軽減税率（8%）：一部の飲食料品や新聞など
  3. 非課税/課税対象外の取引（例：郵便切手、寄附金など)

出力形式（すべて明示的に数字を指定、nullは禁止）：

{
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "store_name": "string",
  "address": "string",
  "phone": "string",
  "invoice_number": "string",
  "amount": 金額（整数、単位：円、税込合計）,
  "payment_method": {
    "type": "string（例：QUICPay、VISAなど）",
    "card_last4": "下4桁"
  },
  "tax": {
    "standard_rate": {
      "taxable": 税抜対象額,
      "tax": 消費税額（切捨て済み）
    },
    "reduced_rate": {
      "taxable": 税抜対象額,
      "tax": 消費税額（切捨て済み）
    },
    "exempt": {
      "amount": 非課税・課税対象外の金額（対象があれば、なければ0）
    }
  },
  "items": [
    {
      "name": "string（品目名）",
      "unit_price": 単価（整数、円）,
      "quantity": 個数（整数）,
      "total": 金額（unit_price × quantity）
    },
    ...
  ]
}

注意点：
- 税率が明示されていなくても、税込金額や「内税」表記から判断してください。
- 消費税額が 0 円でも、課税対象が明らかなら taxable に値を入れてください。
- 明記がなければ各項目は 0 としてください（null は使用しないでください）。
- 「非課税」「課税対象外」の項目が含まれる場合、必ずしも課税対象額と税額の総合計が支払総額にならないことに留意してください。
- 店名や住所などもOCRで取得できる範囲で可能な限り補完してください。
- インボイス番号とは「T」に13桁の数字が続く文字列のことです。この欄のみ、ない場合はnullとしてください。
- 品目名・単価・数量・金額は明確に表記されていればすべて抽出してください。

""" + prompt_appendix

  # GPT-4o へ送信
  response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": "You are a receipt analysis assistant. Extract key fields in Japanese receipts and output JSON only."},
      {
        "role": "user",
        "content": [
          {"type": "text", "text": prompt_text},
          {"type": "image_url", "image_url": {
            "url": f"data:{mime_type};base64,{base64_image}"
          }}
        ]
      }
    ],
    max_tokens=1024,
    temperature=0
  )

  # バッククオート除去処理
  raw = response.choices[0].message.content.strip()
  lines = raw.splitlines()
  if lines[0].strip().startswith("```") and lines[-1].strip().endswith("```"):
    raw_json = "\n".join(lines[1:-1])
  else:
    raw_json = raw

  return json.loads(raw_json)

# スクリプト単体実行時の動作
if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description="レシート画像から整形JSONを抽出します")
  parser.add_argument("image_path", help="レシート画像ファイルのパス（JPEG/PNG等）")
  args = parser.parse_args()

  # 画像を開いて処理
  img = Image.open(args.image_path)
  data = analyze_receipt_image(img)

  # 整形表示
  print(json.dumps(data, ensure_ascii=False, indent=2))

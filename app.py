from flask import Flask, request, redirect, url_for, render_template, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image

from datetime import datetime
import os
import json
import csv
import io
from dotenv import load_dotenv
load_dotenv()

from receipt_parser import analyze_receipt_image

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

class Receipt(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  filename = db.Column(db.String(120), nullable=False)
  uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
  exported = db.Column(db.Boolean, default=False)

  # JSONフィールドをカラムに分離
  receipt_date = db.Column(db.String(10))
  receipt_time = db.Column(db.String(5))
  store_name = db.Column(db.String(120))
  amount = db.Column(db.Integer)
  payment_method = db.Column(db.String(30))
  gpt_response = db.Column(db.Text)

@app.route('/')
def upload_form():
  store_names = [row[0] for row in db.session.query(Receipt.store_name).distinct()]
  payment_methods = [row[0] for row in db.session.query(Receipt.payment_method).distinct()]
  return render_template(
      'upload.html',
      store_names=store_names,
      payment_methods=payment_methods,
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
  return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/upload', methods=['POST'])
def upload():
  file = request.files['receipt']
  filename = secure_filename(file.filename)
  filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
  os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
  file.save(filepath)

  image = Image.open(filepath)

  store_names = [row[0] for row in db.session.query(Receipt.store_name).distinct()]
  payment_methods = [row[0] for row in db.session.query(Receipt.payment_method).distinct()]

  prompt_buf = io.StringIO()

  print("(参考) このユーザーが以前に利用したことのある店名一覧:", file=prompt_buf)
  print("```", file=prompt_buf)
  for sn in store_names:
    print(sn, file=prompt_buf)
  print("```", file=prompt_buf)

  print("", file=prompt_buf)

  print("(参考) このユーザーが以前に利用したことのある支払いカード名一覧:", file=prompt_buf)
  print("```", file=prompt_buf)
  for pm in payment_methods:
    print(pm, file=prompt_buf)
  print("```", file=prompt_buf)

  print("", file=prompt_buf)

  print("その他注意事項:", file=prompt_buf)
  print("""
クレジットカード利用の場合、「レシートの発行日付」と「クレジット利用日」がそれぞれ印字されるのが通常であるが、これらは当然に一致する。
日付はこれら複数の要素を用いて確実にスキャンすることが望ましい。
ユーザーは基本的に「ごく最近」のレシートを投稿することが期待されている。何年も前の日付が抽出された場合は、OCRエラーの可能性が高い。
""", file=prompt_buf)

  data = analyze_receipt_image(image, prompt_appendix=prompt_buf.getvalue())

  payment_method = ""
  if isinstance(data.get("payment_method"), dict):
    d = data["payment_method"]
    payment_method = f"{d.get('type', '')} {d.get('card_last4', '')}"

  receipt = Receipt(
    filename=filename,
    receipt_date=data.get("date"),
    receipt_time=data.get("time"),
    store_name=data.get("store_name"),
    amount=data.get("amount", 0),
    payment_method=payment_method,
    gpt_response=json.dumps(data, ensure_ascii=False),
    exported=False,
  )

  db.session.add(receipt)
  db.session.commit()
  return redirect(url_for('receipts', highlight_id=receipt.id))

@app.route('/manual_entry', methods=['POST'])
def manual_entry():
  receipt = Receipt(
    filename="",  # 手動登録なので画像なし
    receipt_date=request.form.get("date"),  # 例: "2025-05-11"
    receipt_time=request.form.get("time"),  # 例: "14:30"
    store_name=request.form.get("store_name"),
    amount=int(request.form.get("amount", 0)),  # 明示的に整数化
    payment_method=request.form.get("payment_method", ""),
    exported=False
  )
  db.session.add(receipt)
  db.session.commit()
  return redirect(url_for('receipts'))

@app.route('/receipts')
def receipts():
  return render_template('receipts.html')

@app.route("/api/receipts")
def api_receipts():
  show_exported = request.args.get("exported", "false").lower() == "true"
  query = Receipt.query.filter_by(exported=show_exported)

  if show_exported:
    query = query.order_by(Receipt.receipt_date.desc(), Receipt.receipt_time.desc())
  else:
    query = query.order_by(Receipt.receipt_date, Receipt.receipt_time)

  all_receipts = query.all()
  return jsonify({
    "receipts": [
      {
        "id": r.id,
        "filename": r.filename,
        "receipt_date": r.receipt_date,
        "receipt_time": r.receipt_time,
        "store_name": r.store_name,
        "amount": r.amount,
        "payment_method": r.payment_method,
        "exported": r.exported
      } for r in all_receipts
    ]
  })

@app.route("/api/receipt/<int:receipt_id>", methods=["POST"])
def update_receipt(receipt_id):
  receipt = Receipt.query.get_or_404(receipt_id)
  data = request.get_json()

  receipt.store_name = data.get("store_name", receipt.store_name)
  receipt.amount = data.get("amount", receipt.amount)
  receipt.payment_method = data.get("payment_method", receipt.payment_method)
  receipt.receipt_date = data.get("receipt_date", receipt.receipt_date)
  receipt.receipt_time = data.get("receipt_time", receipt.receipt_time)

  db.session.commit()
  return jsonify({"status": "updated"})

@app.route("/api/receipt/<int:receipt_id>", methods=["DELETE"])
def delete_receipt(receipt_id):
  receipt = Receipt.query.get_or_404(receipt_id)
  filepath = os.path.join(app.config['UPLOAD_FOLDER'], receipt.filename)
  if receipt.filename and os.path.exists(filepath):
    os.remove(filepath)
  db.session.delete(receipt)
  db.session.commit()
  return jsonify({"status": "deleted"})

@app.route('/export_csv', methods=['GET', 'POST'])
def export_csv():
  receipts = Receipt.query.filter_by(exported=False).order_by(Receipt.receipt_date, Receipt.receipt_time).all()
  output = []

  if not receipts:
    return jsonify({"status": "empty"}), 204  # No Content

  for r in receipts:
    output.append([r.receipt_date, r.store_name, r.amount])
    r.exported = True
  db.session.commit()
  with open("/tmp/export.csv", "w", encoding="cp932", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["日付", "店名", "金額"])
    writer.writerows(output)
  return send_file("/tmp/export.csv", as_attachment=True, download_name="receipts.csv")

@app.route("/api/receipt_choices")
def api_receipt_choices():
  store_names = [r[0] for r in db.session.query(Receipt.store_name).distinct() if r[0]]
  payment_methods = [r[0] for r in db.session.query(Receipt.payment_method).distinct() if r[0]]
  return jsonify({
    "store_names": store_names,
    "payment_methods": payment_methods
  })


if __name__ == '__main__':
  os.makedirs('uploads', exist_ok=True)
  os.makedirs('instance', exist_ok=True)
  with app.app_context():
      db.create_all()
  app.run(host='0.0.0.0', port=5000, debug=True)

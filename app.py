# search_companyimport os
import pandas as pd
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB 업로드 제한

NTS_API_KEY = os.environ.get("NTS_API_KEY")  # Render나 환경변수에 저장한 국세청 API 키

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

results = []  # 누적 조회 결과 저장 리스트

# 홈 화면
@app.route('/')
def index():
    return render_template('index.html', results=results)

# 파일 업로드 및 국세청 API 조회
@app.route('/upload_biz', methods=['POST'])
def upload_biz():
    file = request.files['file']
    if not file:
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 엑셀 파일에서 사업자등록번호 추출
    df = pd.read_excel(filepath)
    if '사업자등록번호' not in df.columns:
        return "엑셀 파일에 '사업자등록번호' 컬럼이 없습니다."

    bno_list = df['사업자등록번호'].astype(str).str.replace("-", "").tolist()

    # 100건 단위로 분할 조회 (API 제한)
    chunk_size = 100
    for i in range(0, len(bno_list), chunk_size):
        chunk = bno_list[i:i + chunk_size]
        payload = {"b_no": chunk}
        url = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={NTS_API_KEY}"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return f"API 호출 실패: {response.status_code}"

        data = response.json().get("data", [])
        for item in data:
            results.append({
                "사업자등록번호": item.get("b_no", ""),
                "상태": item.get("b_stt", ""),
                "과세유형": item.get("tax_type", ""),
                "폐업일자": item.get("end_dt", ""),
                "조회일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return redirect(url_for('index'))

# 개별 행 삭제
@app.route('/delete_row', methods=['POST'])
def delete_row():
    index = int(request.form['index'])
    if 0 <= index < len(results):
        del results[index]
    return redirect(url_for('index'))

# 전체 초기화
@app.route('/clear_all', methods=['POST'])
def clear_all():
    results.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
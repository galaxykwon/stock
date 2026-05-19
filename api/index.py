from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    token_path = "/tmp/kis_token.txt"
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            saved_token = f.read().strip()
            if saved_token: return saved_token
    url = f"{BASE_URL}/oauth2/tokenP"
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(url, json=body)
    token = res.json().get("access_token")
    if token:
        with open(token_path, "w") as f: f.write(token)
    return token

@app.route('/api/search', methods=['GET'])
def search():
    code = request.args.get('code')
    token = get_access_token()
    headers = {"authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010900", "custtype": "P"}
    # 해당 종목의 투자자 매매추이 조회
    res = requests.get(f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor", headers=headers, params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
    data = res.json().get("output", [])
    # 가장 최신 데이터 반환
    item = data[0] if data else {"frgn_ntby_qty": "0", "orgn_ntby_qty": "0", "prsn_ntby_qty": "0"}
    return jsonify(item)

@app.route('/api/rank', methods=['GET'])
def get_rank():
    market = request.args.get('market') # 1:코스피, 2:코스닥
    investor = request.args.get('investor') # 9000:외인, 8000:기관
    token = get_access_token()
    # 전일 확정 데이터 조회를 위한 날짜 설정
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    headers = {"authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010900", "custtype": "P"}
    
    # 일자별 투자자 매매추이 API 호출 (종목 코드 없이 특정일자 전체 순위 조회)
    res = requests.get(f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-item-investor", headers=headers, 
                       params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930", "FID_INPUT_DATE_1": yesterday, "FID_INPUT_DATE_2": yesterday})
    return jsonify(res.json().get("output", [])[:10])

if __name__ == '__main__': app.run()

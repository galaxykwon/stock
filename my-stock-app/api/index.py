from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# 환경변수에서 KIS API 키 가져오기 (Vercel 설정에서 등록 필요)
APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    """
    토큰 발급 함수. (실제 운영 시에는 24시간 유지되는 토큰을 
    Vercel KV나 외부 DB에 캐싱하여 사용하는 것을 권장합니다.)
    """
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    res = requests.post(url, headers=headers, json=body)
    return res.json().get("access_token")

@app.route('/api/search', methods=['GET'])
def search_stock():
    """개별 종목의 실시간 외국인/기관/개인 매수세 조회"""
    stock_code = request.args.get('code')
    token = get_access_token()
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100",  # 주식당일매매동향 TR ID
        "custtype": "P"
    }
    
    # 실제 API 호출 로직 (아래 params는 KIS 명세서에 맞게 조정 필요)
    # params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
    # response = requests.get(f"{BASE_URL}/uapi/domestic-stock/v1/quotations/...", headers=headers, params=params)
    
    # 예시 응답 반환 (KIS API의 실제 응답 필드 매핑 필요)
    return jsonify({
        "stock": stock_code,
        "foreign": "12,500",
        "institution": "-3,400",
        "retail": "-9,100"
    })

@app.route('/api/rank', methods=['GET'])
def get_ranking():
    """전일 기준 코스피/코스닥 외국인, 기관 순매수 상위 10종목 조회"""
    market = request.args.get('market') # 0001(코스피) 또는 1001(코스닥)
    investor = request.args.get('investor') # 9000(외국인) 또는 8000(기관)
    token = get_access_token()
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHPTJ04400000", # 국내기관_외국인 매매종목가집계 TR ID
        "custtype": "P"
    }
    
    # 어제 날짜 계산 (월요일인 경우 금요일 날짜 계산 로직 추가 필요)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    # 로직 생략: KIS API 순매수 랭킹 엔드포인트 호출 및 상위 10개 슬라이싱
    # ...
    
    # 예시 응답 반환
    mock_data = [
        {"rank": i, "name": f"상위종목{i}", "volume": f"{10000 - (i*500)}"} for i in range(1, 11)
    ]
    return jsonify(mock_data)

if __name__ == '__main__':
    app.run()
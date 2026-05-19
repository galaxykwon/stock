from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Vercel 환경 변수에서 API 키 불러오기
APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")

# 실전투자 URL (모의투자용 키를 발급받으셨다면 https://openapivts.koreainvestment.com:29443 로 변경하세요)
BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    """KIS API 접근 토큰 발급"""
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
    """개별 종목 실시간 투자자 매수동향 조회"""
    stock_code = request.args.get('code')
    
    # 6자리 코드가 아닌 경우 에러 반환
    if not stock_code or len(stock_code) != 6:
        return jsonify({"stock": "입력오류", "foreign": "-", "institution": "-", "retail": "-"})

    token = get_access_token()
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010900", # 주식현재가 투자자 TR ID
        "custtype": "P"
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code
    }
    
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    
    try:
        output = data.get("output", {})
        return jsonify({
            "stock": stock_code,
            "foreign": output.get("frgn_ntby_qty", "0"), # 외국인 순매수
            "institution": output.get("orgn_ntby_qty", "0"), # 기관 순매수
            "retail": output.get("prsn_ntby_qty", "0") # 개인 순매수
        })
    except:
        return jsonify({"stock": stock_code, "foreign": "조회실패", "institution": "조회실패", "retail": "조회실패"})

@app.route('/api/rank', methods=['GET'])
def get_ranking():
    """전일 기준 외국인/기관 순매수 상위 10종목 조회"""
    market = request.args.get('market') # 0001(코스피) 또는 1001(코스닥)
    investor = request.args.get('investor') # 9000(외국인) 또는 8000(기관)
    
    token = get_access_token()
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/foreign-institution-total"
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHPTJ04400000", # 기관_외국인 매매종목가집계 TR ID
        "custtype": "P"
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "11480",
        "FID_DIV_CLS_CODE": "0",
        "FID_RANK_SORT_CLS_CODE": "0", # 0: 순매수 상위
        "FID_ETC_CLS_CODE": "0",
        "FID_TARGET_CLS_CODE": "0",
        "FID_TARGET_CPT_VAL": "0",
        "FID_TARGET_STCK_PRC": "0",
        "FID_TARGET_STCK_VOL": "0",
        "FID_VOL_CNT": "0",
        "FID_KOSPI_MRKT_CLS_CODE": market,
        "FID_KOSDAQ_MRKT_CLS_CODE": "0" if market == "0001" else market,
        "FID_PRDT_CLS_CODE": investor,
        "FID_TRGET_EXLS_CLS_CODE": "0"
    }
    
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    
    result = []
    try:
        items = data.get("output", [])[:10] # 상위 10개만 슬라이싱
        for i, item in enumerate(items):
            result.append({
                "rank": i + 1,
                "name": item.get("hts_kor_isnm", "알수없음"), # 종목 한글명
                "volume": item.get("ntby_qty", "0") # 순매수 수량
            })
    except:
        pass
        
    if not result:
        result = [{"rank": "-", "name": "API 연결/권한 오류", "volume": "-"}]
        
    return jsonify(result)

if __name__ == '__main__':
    app.run()

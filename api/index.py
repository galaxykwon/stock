from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    """토큰을 /tmp 폴더에 저장하여 잦은 재발급(문자 폭탄) 방지"""
    token_path = "/tmp/kis_token.txt"
    
    # 1. 임시 폴더에 캐싱된 토큰이 있으면 그대로 재사용
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            saved_token = f.read().strip()
            if saved_token:
                return saved_token
                
    # 2. 토큰이 없으면 한투 서버에 새로 요청
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    try:
        res = requests.post(url, headers=headers, json=body)
        token = res.json().get("access_token")
        if token:
            # 새로 발급받은 토큰을 임시 파일로 저장해둠
            with open(token_path, "w") as f:
                f.write(token)
        return token
    except:
        return None

@app.route('/api/search', methods=['GET'])
def search_stock():
    """개별 종목 실시간 투자자 매수동향 조회"""
    stock_code = request.args.get('code')
    if not stock_code or len(stock_code) != 6:
        return jsonify({"stock": "입력오류", "foreign": "코드 6자리", "institution": "-", "retail": "-"})

    token = get_access_token()
    if not token:
        return jsonify({"stock": stock_code, "foreign": "토큰오류", "institution": "발급실패", "retail": "-"})

    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010900",
        "custtype": "P"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code
    }
    
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    
    rt_cd = data.get("rt_cd", "1")
    if rt_cd != "0":
        return jsonify({"stock": stock_code, "foreign": f"조회실패", "institution": data.get("msg1", "-"), "retail": "-"})
        
    try:
        output = data.get("output", [])
        
        # 데이터가 리스트로 올 경우 가장 최신(0번째) 데이터를 가져오도록 수정
        if isinstance(output, list) and len(output) > 0:
            today_data = output[0] 
        elif isinstance(output, dict):
            today_data = output
        else:
            today_data = {}

        return jsonify({
            "stock": stock_code,
            "foreign": today_data.get("frgn_ntby_qty", "0"),
            "institution": today_data.get("orgn_ntby_qty", "0"),
            "retail": today_data.get("prsn_ntby_qty", "0")
        })
    except Exception as e:
        return jsonify({"stock": stock_code, "foreign": "파싱에러", "institution": str(e), "retail": "-"})

@app.route('/api/rank', methods=['GET'])
def get_ranking():
    """전일 기준 외국인/기관 순매수 상위 조회"""
    market = request.args.get('market')
    investor = request.args.get('investor')
    
    token = get_access_token()
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/foreign-institution-total"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHPTJ04400000",
        "custtype": "P"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "11480",
        "FID_DIV_CLS_CODE": "0",
        "FID_RANK_SORT_CLS_CODE": "0",
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
    
    rt_cd = data.get("rt_cd", "1")
    if rt_cd != "0":
        return jsonify([{"rank": "-", "name": f"API에러: {data.get('msg1', '')}", "volume": "-"}])
        
    result = []
    try:
        items = data.get("output", [])[:10]
        
        # 장 시작 전이나 휴일 등 데이터가 비어있을 경우에 대한 처리
        if not items:
            return jsonify([{"rank": "-", "name": "조건에 맞는 데이터 없음 (장 미운영 등)", "volume": "-"}])
            
        for i, item in enumerate(items):
            result.append({
                "rank": i + 1,
                "name": item.get("hts_kor_isnm", "알수없음"),
                "volume": item.get("ntby_qty", "0")
            })
    except:
        pass
        
    if not result:
        result = [{"rank": "-", "name": "데이터 파싱 오류", "volume": "-"}]
        
    return jsonify(result)

if __name__ == '__main__':
    app.run()

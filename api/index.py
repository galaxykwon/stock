from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    token_path = "/tmp/kis_token.txt"
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            saved_token = f.read().strip()
            if saved_token:
                return saved_token
                
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
            with open(token_path, "w") as f:
                f.write(token)
        return token
    except:
        return None

def resolve_stock_code(query):
    """한글 종목명을 입력받아 네이버 금융 API를 통해 6자리 코드로 변환"""
    if query.isdigit() and len(query) == 6:
        return query
    try:
        url = f"https://ac.finance.naver.com/ac?q={query}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8"
        res = requests.get(url, timeout=3)
        data = res.json()
        items = data.get("items", [])
        if items and len(items[0]) > 0:
            return items[0][0][1] # 6자리 종목코드 추출
    except:
        pass
    return None

@app.route('/api/search', methods=['GET'])
def search_stock():
    query = request.args.get('code', '').strip()
    if not query:
        return jsonify({"stock": "입력오류", "name": "-", "foreign": "-", "institution": "-", "retail": "-"})

    # 종목명 -> 종목코드 변환
    stock_code = resolve_stock_code(query)
    if not stock_code:
        return jsonify({"stock": "검색실패", "name": query, "foreign": "종목을 찾을 수 없음", "institution": "-", "retail": "-"})

    token = get_access_token()
    if not token:
        return jsonify({"stock": stock_code, "name": query, "foreign": "토큰오류", "institution": "발급실패", "retail": "-"})

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
        return jsonify({"stock": stock_code, "name": query, "foreign": f"조회실패", "institution": data.get("msg1", "-"), "retail": "-"})
        
    try:
        output = data.get("output", [])
        if isinstance(output, list) and len(output) > 0:
            today_data = output[0] 
        elif isinstance(output, dict):
            today_data = output
        else:
            today_data = {}

        f_val = str(today_data.get("frgn_ntby_qty", "")).strip() or "0"
        i_val = str(today_data.get("orgn_ntby_qty", "")).strip() or "0"
        r_val = str(today_data.get("prsn_ntby_qty", "")).strip() or "0"

        return jsonify({
            "stock": stock_code,
            "name": query if not query.isdigit() else stock_code,
            "foreign": f_val,
            "institution": i_val,
            "retail": r_val
        })
    except Exception as e:
        return jsonify({"stock": stock_code, "name": query, "foreign": "파싱에러", "institution": str(e), "retail": "-"})

@app.route('/api/rank', methods=['GET'])
def get_ranking():
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
    
    # KIS API 요구사항에 맞게 '1' 또는 '0'으로 완벽히 분리 처리
    kospi_code = "1" if market == "0001" else "0"
    kosdaq_code = "1" if market == "1001" else "0"
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "11480",
        "FID_INPUT_ISCD": "",  # 종목코드 칸을 완전히 비워야 랭킹이 나옴
        "FID_DIV_CLS_CODE": "0",
        "FID_RANK_SORT_CLS_CODE": "0",
        "FID_ETC_CLS_CODE": "0",
        "FID_TARGET_CLS_CODE": "0",
        "FID_TARGET_CPT_VAL": "0",
        "FID_TARGET_STCK_PRC": "0",
        "FID_TARGET_STCK_VOL": "0",
        "FID_VOL_CNT": "0",
        "FID_KOSPI_MRKT_CLS_CODE": kospi_code,
        "FID_KOSDAQ_MRKT_CLS_CODE": kosdaq_code,
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
        if not items:
            return jsonify([{"rank": "-", "name": "당일 집계된 데이터 없음", "volume": "-"}])
            
        for i, item in enumerate(items):
            volume_val = str(item.get("ntby_qty", "")).strip() or "0"
            result.append({
                "rank": i + 1,
                "name": item.get("hts_kor_isnm", "알수없음"),
                "volume": volume_val
            })
    except:
        pass
        
    if not result:
        return jsonify([{"rank": "-", "name": "데이터 파싱 오류", "volume": "-"}])
        
    return jsonify(result)

if __name__ == '__main__':
    app.run()


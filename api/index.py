from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

APP_KEY = os.environ.get("KIS_APP_KEY")
APP_SECRET = os.environ.get("KIS_APP_SECRET")
BASE_URL = "https://openapi.koreainvestment.com:9443"

# 서버 메모리에 토큰 임시 저장 (잦은 문자 발급 방지)
cached_token = None

def get_access_token():
    global cached_token
    if cached_token:
        return cached_token
        
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
            cached_token = token
        return token
    except:
        return None

@app.route('/api/search', methods=['GET'])
def search_stock():
    stock_code = request.args.get('code')
    if not stock_code or len(stock_code) != 6:
        return jsonify({"stock": "입력오류", "foreign": "코드 6자리 필요", "institution": "-", "retail": "-"})

    token = get_access_token()
    if not token:
        return jsonify({"stock": stock_code, "foreign": "토큰발급실패", "institution": "Key확인필요", "retail": "-"})

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
    
    # 한투 서버가 보내온 에러 메시지가 있다면 화면에 표출
    rt_cd = data.get("rt_cd", "1")
    msg1 = data.get("msg1", "조회 실패")
    
    if rt_cd != "0":
        return jsonify({"stock": stock_code, "foreign": f"실패:{msg1}", "institution": "-", "retail": "-"})
        
    try:
        output = data.get("output", {})
        return jsonify({
            "stock": stock_code,
            "foreign": output.get("frgn_ntby_qty", "0"),
            "institution": output.get("orgn_ntby_qty", "0"),
            "retail": output.get("prsn_ntby_qty", "0")
        })
    except Exception as e:
        return jsonify({"stock": stock_code, "foreign": "파싱에러", "institution": str(e), "retail": "-"})

@app.route('/api/rank', methods=['GET'])
def get_ranking():
    market = request.args.get('market')
    investor = request.args.get('investor')
    
    token = get_access_token()
    if not token:
        return jsonify([{"rank": "-", "name": "토큰 발급 실패", "volume": "-"}])

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
    msg1 = data.get("msg1", "오류")
    
    if rt_cd != "0":
        return jsonify([{"rank": "-", "name": f"에러:{msg1}", "volume": "-"}])
        
    result = []
    try:
        items = data.get("output", [])[:10]
        for i, item in enumerate(items):
            result.append({
                "rank": i + 1,
                "name": item.get("hts_kor_isnm", "알수없음"),
                "volume": item.get("ntby_qty", "0")
            })
    except:
        pass
        
    if not result:
        result = [{"rank": "-", "name": "데이터가 없습니다.", "volume": "-"}]
        
    return jsonify(result)

if __name__ == '__main__':
    app.run()

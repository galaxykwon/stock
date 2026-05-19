def resolve_stock_code(query):
    # 1. 6자리 코드라면 바로 반환
    if query.isdigit() and len(query) == 6:
        return query
    
    # 2. 가장 많이 찾는 종목 사전 등록
    stock_dict = {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
        "삼성바이오로직스": "207940", "현대차": "005380", "셀트리온": "068270",
        "POSCO홀딩스": "005490", "기아": "000270", "KB금융": "105560", "네이버": "035420"
    }
    if query in stock_dict:
        return stock_dict[query]
        
    # 3. 나머지는 기존 야후 API 활용
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=3)
        data = res.json()
        for q in data.get("quotes", []):
            if ".KS" in q.get("symbol", "") or ".KQ" in q.get("symbol", ""):
                return q.get("symbol", "").split(".")[0]
    except:
        pass
    return None

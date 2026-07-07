import os
import sys
import json
import argparse
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# HTML 태그 제거용 정규식 (네이버 API 결과 정제용)
def clean_html(text):
    return re.sub(r'<.*?>', '', text)

# 1. CLI 인자 파싱 및 날짜 검증
def parse_args():
    parser = argparse.ArgumentParser(description="LLM과 지도 API를 활용한 국내 여행 추천 프로그램")
    parser.add_argument("-date", required=True, help="여행 날짜 (형식: YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        valid_date = datetime.strptime(args.date, "%Y-%m-%d")
        return valid_date.strftime("%Y-%m-%d")
    except ValueError:
        print("❌ 오류: 날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식으로 입력해주세요.")
        sys.exit(1)

# 2. 환경변수 및 API 키 확인
def check_api_keys():
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    naver_id = os.getenv("NAVER_CLIENT_ID")
    naver_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not gemini_key or not naver_id or not naver_secret:
        print("❌ 오류: API 키가 설정되지 않았습니다.")
        print("프로젝트 루트에 .env 파일을 생성하고 아래 값을 설정해주세요:")
        print("GEMINI_API_KEY=...\nNAVER_CLIENT_ID=...\nNAVER_CLIENT_SECRET=...")
        sys.exit(1)
    
    client = genai.Client(api_key=gemini_key)
    return client, naver_id, naver_secret

# 3. LLM API 연동 - 여행지 추천 (JSON 출력)
def get_recommendation(client, date_str, errors):
    print(f"✈️  [{date_str}] 여행지 추천을 위해 LLM에 요청 중...")
    
    prompt = f"""
    사용자가 {date_str}에 국내 여행을 가려고 합니다. 이 시기에 방문하기 가장 좋은 대한민국의 도시 1곳을 추천해주세요.
    반드시 아래의 JSON 형식으로만 응답해야 하며, 다른 텍스트나 마크다운 기호(```json 등)는 제외하세요.
    
    {{
        "recommended_city": "도시 이름 (예: 제주, 강릉)",
        "weather": "이 시기의 일반적인 날씨 요약 (1-2문장)",
        "events": ["행사나 축제 후보 1", "행사나 축제 후보 2"],
        "reason": "이 도시를 추천하는 구체적인 이유 (2-4문장)"
    }}
    """
    
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            
            required_keys = ["recommended_city", "weather", "events", "reason"]
            if all(key in data for key in required_keys):
                print(f"✅ 추천 도시: {data['recommended_city']}")
                return data
            else:
                raise ValueError("JSON 응답에 필수 키가 누락되었습니다.")
                
        except (json.JSONDecodeError, ValueError, Exception) as e:
            if attempt == 0:
                print("⚠️  LLM JSON 파싱 실패, 재요청합니다...")
            else:
                error_msg = f"LLM 추천 오류: {str(e)}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
                return None

# 4. 지도 API 연동 - 네이버 로컬 검색 (맛집)
def get_restaurants(city, naver_id, naver_secret, errors):
    print(f"🔍 '{city}' 맛집 정보를 네이버 API로 검색 중...")
    
    # [핵심 수정] 에디터의 강제 링크 변환을 완벽히 차단하기 위해 리스트로 쪼갠 뒤 합칩니다.
    url_parts = ["https://", "openapi", ".naver", ".com", "/v1/search/local.json"]
    url = "".join(url_parts)
    
    headers = {
        "X-Naver-Client-Id": naver_id,
        "X-Naver-Client-Secret": naver_secret
    }
    params = {
        "query": f"{city} 맛집",
        "display": 5,
        "sort": "comment"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            restaurants = []
            for item in items:
                restaurants.append({
                    "name": clean_html(item.get("title", "")),
                    "address": item.get("roadAddress") or item.get("address", ""),
                    "category": item.get("category", ""),
                    "url": item.get("link", ""),
                    "mapx": item.get("mapx", ""),
                    "mapy": item.get("mapy", "")
                })
            
            print(f"✅ 맛집 {len(restaurants)}곳 검색 완료.")
            return restaurants
        else:
            error_msg = f"네이버 API 호출 실패: HTTP {response.status_code}"
            print(f"⚠️  {error_msg}")
            errors.append(error_msg)
            return []
            
    except Exception as e:
        error_msg = f"네이버 API 요청 중 네트워크 오류: {str(e)}"
        print(f"⚠️  {error_msg}")
        errors.append(error_msg)
        return []

# 5. LLM API 연동 - 최종 리포트 생성 (Markdown)
def generate_final_report(client, date_str, rec_data, restaurants, errors):
    print("📝 최종 여행 리포트 생성 중...")
    
    if not restaurants:
        rest_str = "맛집 데이터 없음 (검색 실패 또는 결과 없음)"
    else:
        rest_str = json.dumps(restaurants, ensure_ascii=False, indent=2)
        
    prompt = f"""
    당신은 전문 여행 플래너입니다. 아래 제공된 데이터를 바탕으로 매력적인 국내 여행 최종 리포트를 Markdown 형식으로 작성해주세요.

    [여행 날짜]: {date_str}
    [추천 지역 및 기본 정보]: {json.dumps(rec_data, ensure_ascii=False, indent=2)}
    [맛집 리스트]: {rest_str}
    
    다음 항목들이 리포트에 반드시 포함되어야 합니다:
    1. 추천 지역 + 추천 이유 요약
    2. 해당 시기의 날씨 요약
    3. 행사/축제 목록
    4. 맛집 리스트 (0건일 경우 "데이터 없음"으로 자연스럽게 표기)
    5. 위 정보를 바탕으로 한 1일 추천 일정 제안 (오전/오후/저녁 구분)
    
    가독성 좋은 마크다운 포맷(헤더, 리스트 등)을 사용하여 친절한 어투로 작성해주세요.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        print("✅ 리포트 생성 완료.")
        return response.text
    except Exception as e:
        error_msg = f"리포트 생성 중 오류 발생: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)
        return f"# 리포트 생성 실패\n\n오류 내용: {str(e)}"

# 6. 결과 저장
def save_results(date_str, rec_data, restaurants, report_md, errors):
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    raw_data = {
        "date": date_str,
        "recommendation": rec_data,
        "restaurants": restaurants,
        "errors": errors
    }
    
    json_filename = f"results/travel_data_{timestamp}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=4)
        
    md_filename = f"results/travel_report_{timestamp}.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"\n📂 파일 저장 완료!")
    print(f" - JSON 데이터: {json_filename}")
    print(f" - MD 리포트: {md_filename}")

# 메인 실행 로직
def main():
    date_str = parse_args()
    client, naver_id, naver_secret = check_api_keys()
    
    errors = []
    
    # Step 1: 추천 지역 받기
    rec_data = get_recommendation(client, date_str, errors)
    if not rec_data:
        print("❌ 여행지 추천 데이터를 받아오지 못해 프로그램을 종료합니다.")
        sys.exit(1)
        
    # Step 2: 맛집 검색
    restaurants = get_restaurants(rec_data["recommended_city"], naver_id, naver_secret, errors)
    
    # Step 3: 최종 리포트 생성
    report_md = generate_final_report(client, date_str, rec_data, restaurants, errors)
    
    # Step 4: 결과 저장
    save_results(date_str, rec_data, restaurants, report_md, errors)

if __name__ == "__main__":
    main()
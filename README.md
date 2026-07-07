# 프로그램 개요
- LLM API (gemini-2.5-flash API )와 지도 API(Naver 검색 API) 를 조합한 국내 여행지를  추천해주는 프로그램으로써, 사용자가 여행 날짜를 입력하면, LLM이 해당 시기에 여행하기 좋은 지역을 추천하고, 지도 API로 맛집 정보를 검색한 뒤, 최종 여행 리포트를 생성합니다.


# 실행방법
- Power Shell 창을 열어서 실행
예) Python A2_1_Project.py -date "2026-08-01"
프로그램 실행시 원하시는 날짜를 “yyyy-mm-dd” 형태로 입력해주세요.


# API 설정방법
 1. Google Gemini API Key : Google AI Studio 접속하여 발급받음 (https://aistudio.google.com/)
 2. 네이버 지역 검색 API 키 : 네이버 개발자 센터 접속 및 로그인하여 발급받음  (https://developers.naver.com/)
 3. .env 파일에 키를 복사하여 붙여 넣음
    * 기존에 발급받은 Gemini 키
    GEMINI_API_KEY=키값 

    * 새로 발급받은 네이버 키 (따옴표 없이 작성)
    NAVER_CLIENT_ID= Client_ID값
    NAVER_CLIENT_SECRET=Client_Secret값


# 결과물 확인방법
- results/ 폴더에 최종 여행 리포트 Markdown 파일을 열어 확인


# API 유출 관련 주의 사항 포함
- “절대 코드에 API Key를 직접 적지 마세요.** 
   깃허브(GitHub) 등에 유출되면 큰일 납니다! 
   (.env 환경 변수 파일에 숨겨서 관리)


 

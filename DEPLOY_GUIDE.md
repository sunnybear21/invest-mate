# Invest Mate 웹 배포 가이드 (Streamlit Cloud)

이 프로그램을 인터넷에서 누구나 접속할 수 있는 **웹 사이트**로 만드는 방법입니다.

---

## 1. 사전 준비 (필수)
배포를 위해서는 소스 코드를 **GitHub(깃허브)**라는 코드 저장소에 올려야 합니다.

1.  **[GitHub 가입](https://github.com/)**: 계정이 없다면 만듭니다.
2.  **새 저장소(New Repository) 생성**:
    *   Repository name: `invest-mate` (원하는 이름)
    *   Public(공개) 선택
    *   Create repository 클릭

---

## 2. 파일 업로드
내 컴퓨터의 파일들을 GitHub에 올립니다. (Git 명령어를 쓰거나, 웹에서 드래그 앤 드롭)

**업로드해야 할 파일/폴더:**
```
invest-mate/
├── .streamlit/
│   └── config.toml        # 테마 설정
├── apps/
│   ├── app_main.py        # 메인 앱 (저널 + 차트분석)
│   ├── app_lucy.py
│   ├── app_sunny.py
│   └── trading_journal_app.py
├── src/
│   ├── __init__.py
│   ├── auth.py
│   ├── chart_generator.py
│   ├── database.py
│   ├── lucy_scanner_realtime.py
│   ├── smart_money_analyzer.py
│   └── naver_stock_themes.json
├── requirements.txt        # (필수!)
└── sunny_logo.png
```

**주의**:
- `data/` 폴더는 올리지 않는 것이 좋습니다 (웹에서는 데이터베이스가 새로 생성됩니다)
- `venv/` 폴더는 올리면 안됩니다 (용량이 큼)
- `.bat` 파일들은 윈도우용이므로 웹에선 필요 없지만 올려도 상관없습니다

---

## 3. Streamlit Cloud 배포

### 3-1. 기본 배포 (SQLite - 테스트용)
1.  **[Streamlit Cloud](https://streamlit.io/cloud)** 접속 및 로그인 (GitHub 계정 연동).
2.  **New app** 클릭.
3.  **Deploy an app** 설정:
    *   **Repository**: 방금 만든 `invest-mate` 선택
    *   **Branch**: `main` 또는 `master`
    *   **Main file path**: `apps/app_main.py` (중요!)
    *   **Deploy!** 버튼 클릭

배포 완료 후 `https://your-app-name.streamlit.app` 주소가 생성됩니다.

### 3-2. Google Sheets 연동 (영구 저장용)
데이터를 영구 저장하려면 Google Sheets를 사용합니다. 자세한 설정은 `GSHEETS_SETUP.md`를 참고하세요.

**Streamlit Cloud Secrets 설정:**
1. Streamlit Cloud에서 앱 설정(Settings) > Secrets
2. 아래 형식으로 입력:
```toml
sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

---

## 4. 문제 해결

### 차트가 안 불러지는 경우
- 종목코드가 올바른지 확인 (예: 삼성전자 = 005930)
- pykrx 라이브러리가 장 마감 후에는 더 잘 작동합니다
- Streamlit Cloud에서 한국 시간대 문제가 있을 수 있음

### 데이터가 사라지는 경우
- SQLite 사용 시 Streamlit Cloud가 재시작되면 데이터가 초기화됩니다
- **해결책**: Google Sheets 연동 사용 (위 3-2 참고)

### 배포 실패 시
- `requirements.txt`가 있는지 확인
- Main file path가 정확한지 확인
- GitHub 저장소가 Public인지 확인

---

## 5. 기능 요약
- **차트 분석 (Chart Analysis)**: SMC(Smart Money Concepts) 기반 Order Block, FVG 분석
- **매매 일지 (Trading Journal)**: 매매 기록, PnL 추적, ROI 계산
- **회원 시스템**: 로그인/회원가입 (bcrypt 암호화)

# Google Sheets 연동 가이드

웹(Streamlit Cloud) 배포 시 데이터 저장을 위해 Google Sheets를 연결하는 방법입니다.

## 1. 구글 클라우드 설정
1.  [Google Cloud Console](https://console.cloud.google.com/) 접속.
2.  새 프로젝트 생성 (예: `invest-mate`).
3.  **API 및 서비스 > 라이브러리** 메뉴 이동.
4.  다음 두 가지 API를 검색해서 **사용 설정(Enable)** 합니다:
    *   `Google Sheets API`
    *   `Google Drive API`
5.  **API 및 서비스 > 사용자 인증 정보(Credentials)** 이동.
6.  **사용자 인증 정보 만들기(Create Credentials)** -> **서비스 계정(Service Account)** 선택.
7.  이름 입력 후 생성 완료.
8.  생성된 서비스 계정 클릭 -> **키(Keys)** 탭 -> **키 추가** -> **새 키 만들기** -> **JSON** 선택.
9.  사용자 컴퓨터에 **JSON 파일**이 다운로드됩니다. (이 파일 내용이 필요합니다!)

## 2. 구글 시트 준비
1.  [Google Sheets](https://docs.google.com/spreadsheets/)에서 새 스프레드시트를 만듭니다.
2.  시트 이름은 아무거나 상관없습니다.
3.  브라우저 주소창의 URL 전체를 복사해둡니다. (예: `https://docs.google.com/spreadsheets/d/1XyZ.../edit`)
4.  **공유(Share)** 버튼 클릭.
5.  아까 다운로드 받은 JSON 파일 안에 있는 `client_email` 주소(예: `invest-mate@...iam.gserviceaccount.com`)를 복사해서, 시트 **공유 대상**에 추가하고 **편집자(Editor)** 권한을 줍니다.

## 3. Streamlit Cloud 비밀 키 설정
1.  GitHub에 코드를 올리고 Streamlit Cloud에 배포합니다.
2.  Streamlit Cloud 대시보드에서 앱의 **Settings** -> **Secrets** 클릭.
3.  아래 형식으로 내용을 복사붙여넣기 합니다.

```toml
sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----..."
client_email = "..."
client_id = "..."
auth_uri = "..."
token_uri = "..."
auth_provider_x509_cert_url = "..."
client_x509_cert_url = "..."
```

*   `sheet_url`: 아까 만든 구글 시트 주소
*   `[gcp_service_account]` 아래 내용: 다운받은 **JSON 파일 내용 전체**를 복사해서 붙여넣습니다. (단, JSON의 큰따옴표 형식이 TOML과 호환되게 주의, 위 예시처럼 key = "value" 형태로 변환하거나 JSON 자체를 문자열로 넣을 수도 있지만, 위처럼 TOML 섹션으로 풀어서 쓰는 것이 가장 관리하기 쉽습니다.)

**팁**: JSON 내용을 TOML로 바꾸기 귀찮다면, 아래처럼 JSON을 통째로 넣는 방법도 있습니다 (코드 수정 필요 없음, Streamlit이 알아서 인식).

```toml
sheet_url = "구글시트주소"

[gcp_service_account]
# JSON 파일 내용을 복사해서 여기에 붙여넣으세요.
# 따옴표 등을 TOML 서식에 맞게 좀 다듬어야 할 수 있습니다. 
# 가장 쉬운건 JSON 파일의 중괄호 {} 내용을 그대로 toml format으로 변환해주는 사이트를 이용하는 것입니다.
```

설정이 완료되면 앱이 자동으로 재부팅되면서 **Google Sheets Backend** 모드로 전환됩니다.

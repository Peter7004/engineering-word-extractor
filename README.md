# Engineering Word Extractor

Python 3.11 이상에서 실행하는 한국어 Streamlit 앱입니다. 전기공학·반도체공정 PDF의 사전 용어와 신규 영단어 후보를 수집합니다. AI API나 Google Sheets API를 사용하지 않습니다. 로컬 실행 시 PDF는 내 컴퓨터에서, 클라우드 배포 시에는 배포 서버에서 처리됩니다. 업로드 PDF를 파일로 저장하지 않습니다.

## Streamlit Community Cloud 배포

GitHub 저장소의 최상위에 `app.py`, `requirements.txt`, `dictionaries/`를 올립니다. ZIP 자체를 올리는 것만으로는 배포할 수 없습니다.

1. https://share.streamlit.io 에 GitHub 계정으로 로그인합니다.
2. Create app에서 GitHub 배포를 선택합니다.
3. Repository: `Peter7004/engineering-word-extractor`
4. Branch: `main`
5. Main file path: `app.py`
6. Advanced settings의 Python 버전은 검증한 `3.13`을 선택하고 Deploy를 누릅니다.

위 경로는 프로젝트 파일을 저장소 최상위에 배치한 경우입니다. 폴더째 업로드했다면 실제 `app.py` 위치를 지정해야 합니다. 배포 실패 시 Manage app의 로그에서 첫 오류를 확인하세요. `requirements.txt`와 두 사전 파일을 반드시 포함하세요. 배포 성공 후 공개 앱의 `https://…streamlit.app` 주소를 공유하면 다른 사람도 브라우저로 사용할 수 있습니다.

## Windows 실행

이 폴더에서 PowerShell을 열고 실행하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

이미 Python 환경을 준비했다면 다음 명령도 사용할 수 있습니다.

```powershell
pip install -r requirements.txt
streamlit run app.py
```

분야 선택 → PDF 업로드 → 분석 실행 → 두 탭에서 검색·빈도 필터 및 선택 → CSV 다운로드 순서로 사용합니다. 기존 용어는 기본 선택, 신규 후보는 기본 미선택입니다. 전체 선택/해제는 현재 표시된 단어에 적용되며 숨겨진 단어의 선택도 유지됩니다. 분야·PDF 내용·사전 내용 변경 시 결과와 선택이 초기화되므로 다시 분석하세요.

## 사전 확장

`dictionaries/electrical.csv`, `dictionaries/semiconductor.csv`를 UTF-8 또는 UTF-8 BOM으로 저장하세요. 헤더는 정확히 `term,meaning`이며 쉼표가 포함된 뜻은 큰따옴표로 감쌉니다. 공백·대소문자·중복을 정리합니다. 뜻 충돌은 알림을 표시하고 먼저 읽은 항목을 사용합니다. 통합 시 전기공학 사전을 먼저 읽습니다.

긴 복합 용어부터 매칭하고 이미 매칭된 구간은 재사용하지 않습니다. 복수형·어형 변화·철자 변형은 자동 추론하지 않으므로 필요한 표현을 사전에 직접 추가하세요. 줄 끝 하이픈은 분리된 단어로 보고 연결합니다. 실제 하이픈이 줄 끝에 놓인 경우에는 원문과 달라질 수 있습니다. OCR은 지원하지 않으며 텍스트 없는 페이지는 안내 후 제외합니다. 대형 PDF나 매우 큰 사전은 처리 시간이 길어질 수 있습니다.

## CSV

`extracted_words.csv`는 UTF-8 BOM, 헤더 없는 단일 열입니다. 선택한 영어 표현만 소문자로 저장하며 복합 용어는 한 셀에 유지합니다. 중복 제거 후 빈도 내림차순·동률 알파벳순으로 정렬합니다. Google 스프레드시트의 파일 → 가져오기로 불러오면 A1부터 입력됩니다. 선택이 없으면 다운로드가 비활성화됩니다.

## 검증

```powershell
python -m unittest discover -s tests -v
```

표준 unittest로 사전·매칭·PDF 오류·상태 초기화·CSV를 검사하고 Streamlit AppTest로 검색·필터 선택 유지 및 전체 선택/해제를 검사합니다. 브라우저의 실제 PDF 업로드와 Google 스프레드시트 가져오기는 별도 수동 확인이 필요합니다.

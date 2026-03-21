# AI Collaboration Tool v2 — 개발 환경 세팅 가이드

## 사전 준비 (시스템 설치)

### 1. MySQL 설치
- 공식 사이트에서 macOS용 설치: https://dev.mysql.com/downloads/mysql/
- 설치 후 시스템 환경변수에 mysql 경로 추가 (기본 경로: `/usr/local/mysql/bin`)

### 2. Node.js 설치
- 공식 사이트에서 LTS 버전 설치: https://nodejs.org

### 3. FFmpeg 설치 (STT 기능 사용 시 필요)
```bash
brew install ffmpeg
```

---

## 백엔드 세팅

### 1. MySQL DB 생성
```bash
/usr/local/mysql/bin/mysql -u root -p
```
```sql
CREATE DATABASE infloop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 2. .env 파일 작성
`backend/.env` 파일에 아래 내용 입력:
```
OPENAI_API_KEY=sk-...          # OpenAI API 키
HF_TOKEN=hf_...                # Hugging Face 토큰 (Pyannote 화자분리용)
DB_USER=root
DB_PASSWORD=your_mysql_password
```

### 3. 가상환경 생성 및 패키지 설치
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> `requirements.txt`가 없는 경우 아래 명령으로 직접 설치:
> ```bash
> pip install django djangorestframework django-cors-headers channels daphne PyMySQL python-dotenv faster-whisper pyannote.audio torch openai boto3 html2docx python-docx
> ```

### 4. DB 마이그레이션
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. 초기 데이터 삽입
```bash
python manage.py loaddata data_backup_fixed.json
```

### 6. 백엔드 서버 실행
```bash
python manage.py runserver
```
→ http://localhost:8000

---

## 프론트엔드 세팅

```bash
cd frontend
npm install
npm start
```
→ http://localhost:3000

---

## 매번 서버 켤 때

### 백엔드
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

### 프론트엔드
```bash
cd frontend
npm start
```

---

## 주요 환경 정보

| 항목 | 버전 |
|------|------|
| Python | 3.13 |
| Django | 6.0.3 |
| Node.js | LTS |
| MySQL | 8.x |
| PyMySQL | 1.1.2 (mysqlclient 대체) |
| faster-whisper | 1.2.1 |
| pyannote.audio | 4.0.4 |
| torch | 2.10.0 |

## 알려진 경고 (무시해도 됨)

- **torchcodec 경고**: FFmpeg 미설치 시 발생, STT 기능 외 서버 동작에 무관
- **source map 경고**: react-datepicker 라이브러리 내부 문제, 동작에 무관
- **no-unused-vars**: ESLint 경고, 빌드/실행에 무관

import axios from "axios";

// 백엔드 기본 URL 설정
const BASE_URL = "http://127.0.0.1:8000";

const instance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // 모든 요청에 쿠키 포함 (세션 인증)
  headers: {
    "Content-Type": "application/json",
  },
});

// 요청 인터셉터 (필요시 사용, 현재는 에러 로깅만)
instance.interceptors.request.use(
  (config) => {
    // 요청 전 수행할 작업 (예: 토큰 헤더 추가 등)
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 (공통 에러 처리)
instance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // ✅ CanceledError는 정상적인 cleanup이므로 로그에서 제외
    if (axios.isCancel(error) || error.code === 'ERR_CANCELED') {
      // 취소된 요청은 조용히 무시
      return Promise.reject(error);
    }
    
    // 실제 에러만 콘솔에 출력
    console.error("API Error:", error);
    
    // 공통 에러 처리 로직 (예: 401 시 로그인 페이지로 이동)
    if (error.response?.status === 401) {
      // 예: window.location.href = '/';
    }
    
    return Promise.reject(error);
  }
);

export default instance;
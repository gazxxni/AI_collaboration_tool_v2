/* eslint-disable */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios'; // API 모듈 import
import './Login.css';

function Login() {
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  // 로그인 관리 API
  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      user_id: userId,
      password: password,
    };

    console.log("Payload being sent to the server:", payload);

    try {
      // axios 모듈 사용 (URL 단축, 인증 설정 자동 적용)
      const response = await api.post('/api/users/login/', payload);
      
      console.log("Server Response:", response.data);
      alert(response.data.message);

      // 로그인 성공 시 메인 페이지로 이동
      navigate('/main');
    } catch (error) {
      if (error.response) {
        console.error("Error Response from server:", error.response.data);
        alert(error.response.data.message);
      } else {
        console.error("Error:", error.message);
        alert("An error occurred");
      }
    }
  };

  return (
    <div className="App">
      <div className="Login_page">
        <div className="Login_page1">
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              marginTop: '5px',
            }}
          ></div>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div className="Login_container">
              <img className="Login_logoimage" alt="teamlogo" src="/testlogo.png"  style={{ "--dur": "2.8s" }} />
            </div>
            <form onSubmit={handleSubmit}>
              <div className="Login_input">
                <input
                  type="text"
                  className="Login_userId"
                  id="userId"
                  placeholder="아이디"
                  autoFocus
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                />
                <input
                  type="password"
                  className="Login_password"
                  id="password"
                  placeholder="비밀번호"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                ></input>
                <button id="Login_loginBut">로그인</button>
              </div>
            </form>
            <div
              className="Login_link"
              style={{
                justifyContent: 'center',
                alignItems: 'center',
                display: 'flex',
              }}
            >
              <p
                style={{
                  fontSize: '12px',
                  marginTop: '60px',
                }}
              >
                회사명: (주)무한루프 | 대표: 정세준 | 대표 번호: 010-1234-1234 | 메일 문의:
                jeongsejan@gmail.com
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
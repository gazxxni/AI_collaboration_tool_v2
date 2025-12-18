/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import axios from "axios"; // ✅ axios 직접 사용
import ChatList from "./ChatList"; 
import "./Chat.css"; 

// ✅ 쿠키 전송 설정 (기존 방식 복구)
axios.defaults.withCredentials = true;

const Chat = ({ onClose, initTab = "project", initRoomId = null, initPartner = "" }) => {
  const [userId, setUserId] = useState(null);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [projectName, setProjectName] = useState(""); 
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState("");
  const [socket, setSocket] = useState(null);
  const chatMessagesRef = useRef(null); 
  const wsRef = useRef(null);
  const connectedRef = useRef(false);

  const [activeTab, setActiveTab] = useState("project");      
  const [selectedDmRoomId, setSelectedDmRoomId] = useState(null);
  const [dmPartnerName, setDmPartnerName] = useState("");     
  const isComposing = (e) =>
    e.isComposing || e.nativeEvent?.isComposing || e.keyCode === 229;

  const toDate = (m) => {
    if (m?.timestampDate instanceof Date) return m.timestampDate;
    if (m?.timestamp_iso) {
      const d = new Date(m.timestamp_iso);
      if (!isNaN(d)) return d;
    }
    if (typeof m?.timestamp === "string") {
      const parts = m.timestamp.match(/^(\d{1,2})\/(\d{1,2}) (\d{1,2}):(\d{2})$/);
      if (parts) {
        const [, M, D, H, Min] = parts;
        const y = new Date().getFullYear();
        const d = new Date(`${y}-${String(M).padStart(2,"0")}-${String(D).padStart(2,"0")}T${String(H).padStart(2,"0")}:${Min}:00+09:00`);
        if (!isNaN(d)) return d;
      }
    }
    return new Date(); 
  };

  const normalize = (raw) => ({
    ...raw,
    timestampDate: toDate(raw),
  });

  useEffect(() => {
    if (initTab === "dm" && initRoomId) {
      setActiveTab("dm");
      setSelectedDmRoomId(initRoomId);
      if (initPartner) setDmPartnerName(initPartner);
    }
    if (initTab === "project" && initRoomId) {
      setActiveTab("project");
      setSelectedProjectId(initRoomId);
    }
  }, []);   


  const formatTime = (tsDate) => {
    const d = tsDate instanceof Date ? tsDate : new Date(tsDate);
    if (isNaN(d)) return "";
    return d.toLocaleTimeString("ko-KR", { hour: "numeric", minute: "numeric", hour12: true });
  };

  const shouldShowDate = (cur, prev) => {
    if (!prev) return true;
    const c = cur.timestampDate, p = prev.timestampDate;
    if (!(c instanceof Date) || isNaN(c) || !(p instanceof Date) || isNaN(p)) return false;
    const cd = c.toLocaleDateString("ko-KR", { year:"numeric", month:"numeric", day:"numeric" });
    const pd = p.toLocaleDateString("ko-KR", { year:"numeric", month:"numeric", day:"numeric" });
    return cd !== pd;
  };

  
  // 사용자 ID 가져오기
  useEffect(() => {
    const fetchUser = async () => {
      try {
        // ✅ 전체 URL 명시
        const res = await axios.get("http://127.0.0.1:8000/api/users/name/");
        if (res.data.user_id) {
          setUserId(parseInt(res.data.user_id));
        }
      } catch (err) {
        console.error("사용자 정보 로드 실패", err);
      }
    };
    fetchUser();
  }, []);
  
  // 프로젝트 이름 가져오기
  useEffect(() => {
    if (activeTab !== "project") return;
    
    if (!selectedProjectId && !selectedDmRoomId) {
      setProjectName("선택된 채팅방 없음");
      setDmPartnerName("선택된 채팅방 없음")
      return;
    }
    if (connectedRef.current) return;       
    
    const fetchProjectName = async () => {
      try {
        // ✅ [수정됨] 올바른 경로 + 전체 URL
        const res = await axios.get(`http://127.0.0.1:8000/api/project_name/${selectedProjectId}/`);
        if (res.data.project_name) {
          setProjectName(res.data.project_name);
        } else {
          setProjectName("알 수 없는 프로젝트");
        }
      } catch (err) {
        console.error("프로젝트 이름 로드 실패", err);
        setProjectName("프로젝트 로드 실패");
      }
    };
    fetchProjectName();
  }, [selectedProjectId, activeTab]); 
  
  // 메시지 불러오기
  useEffect(() => {
    if (userId === null) return;
  
    const fetchMessages = async () => {
      try {
        let res;
        if (activeTab === "project") {
          if (!selectedProjectId) return;
          // ✅ [수정됨] 올바른 경로 + 전체 URL
          res = await axios.get(`http://127.0.0.1:8000/api/messages/${selectedProjectId}/`);
          if (res.data.messages) {
            setMessages(res.data.messages.map(normalize));
          }
        } else {
          if (!selectedDmRoomId) return;
          // ✅ [수정됨] 올바른 경로 + 전체 URL
          res = await axios.get(`http://127.0.0.1:8000/api/dm_rooms/${selectedDmRoomId}/messages/`);
          if (res.data.messages) {
            setMessages(res.data.messages.map(m => normalize({ ...m, isMine: m.user_id === userId })));
          }
        }
      } catch (err) {
        console.error("메시지 로드 실패", err);
      }
    };
    fetchMessages();
  }, [selectedProjectId, selectedDmRoomId, userId, activeTab]); 
  
  // WebSocket 연결
  useEffect(() => {
    if (socket) {
      socket.close();
    }
  
    let wsUrl = null;
    // ✅ 127.0.0.1 사용 (안정성 확보)
    if (activeTab === "project") {
      if (!selectedProjectId) return;
      wsUrl = `ws://127.0.0.1:8000/chat/ws/chat/${selectedProjectId}/`;
    } else {
      if (!selectedDmRoomId) return;
      wsUrl = `ws://127.0.0.1:8000/chat/ws/chat/dm/${selectedDmRoomId}/`;
    }
  
    const newSocket = new WebSocket(wsUrl);
    newSocket.onopen = () => console.log("✅ WebSocket 연결 성공!", wsUrl);
    newSocket.onerror = (error) => console.error("🚨 WebSocket 오류 발생:", error);
    newSocket.onclose = () => console.log("❌ WebSocket 연결이 닫혔습니다.");
  
    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const msg = normalize(data); 
      setMessages((prev) => {
        if (msg.temp_id) {
          const idx = prev.findIndex(m => m.message_id === msg.temp_id);
          if (idx !== -1) {
            const copy = [...prev];
            copy[idx] = { ...copy[idx], ...msg, pending: false };
            return copy;
          }
        }
        if (msg.message_id && prev.some(m => m.message_id === msg.message_id)) return prev;
        return [...prev, msg];
      });
    };
  
    setSocket(newSocket);
    return () => {
      if (newSocket) newSocket.close();
    };
  }, [selectedProjectId, selectedDmRoomId, activeTab]); 
  
  const parseTimestamp = (timestamp) => {
    if (!timestamp) return new Date();
    const amPmMatch = timestamp.match(/(오전|오후) (\d+):(\d+)/);
    if (amPmMatch) {
      let hour = parseInt(amPmMatch[2], 10);
      const minute = amPmMatch[3];
      if (amPmMatch[1] === "오후" && hour !== 12) hour += 12;
      else if (amPmMatch[1] === "오전" && hour === 12) hour = 0;
      const now = new Date();
      const formattedDate = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
        hour,
        minute
      );
      if (!isNaN(formattedDate.getTime())) return formattedDate;
    }
    const parts = timestamp.match(/(\d+)\/(\d+) (\d+):(\d+)/);
    if (parts) {
      const month = parts[1].padStart(2, "0");
      const day = parts[2].padStart(2, "0");
      const hour = parts[3].padStart(2, "0");
      const minute = parts[4].padStart(2, "0");
      const year = new Date().getFullYear();
      const formattedDate = new Date(
        `${year}-${month}-${day}T${hour}:${minute}:00+09:00`
      );
      if (!isNaN(formattedDate.getTime())) return formattedDate;
    }
    console.warn("🚨 알 수 없는 타임스탬프 형식:", timestamp);
    return new Date();
  };
  
  const sendMessage = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (!message.trim()) return;

    const tempId = `local-${Date.now()}`;
    const mine = {
      message_id: tempId,
      message,
      user_id: userId,
      username: "(나)",
      timestampDate: new Date(),  
      pending: true,              
    };

    setMessages((prev) => [...prev, mine]);

    const payload = { message, user_id: userId, temp_id: tempId };
    socket.send(JSON.stringify(payload));
    setMessage("");
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [messages]);
  
  return (
    <div className="Invite_overlay" onClick={onClose}>
      <div className="Invite_modal" onClick={(e) => e.stopPropagation()} >
        <button className="Invite_close_btn" onClick={onClose}>
          ✖
        </button>
        <div className="Invite_app">
          <div className="Invite_page">
            <div className="Chat_page2">
              <div className="chat-container">

                {/* 좌측: 선택한 채팅방 메시지 화면 */}
                <div className="chat-box">
                  <div className="chat-header">
                    <h3>
                      🔔{" "}
                      {activeTab === "project" ? projectName : dmPartnerName}
                    </h3>
                  </div>

                  <div className="chat-messages" ref={chatMessagesRef}>
                    {messages.map((msg, index) => {
                      const prev = index > 0 ? messages[index - 1] : null;
                      const showDate = shouldShowDate(msg, prev);
                      return (
                        <React.Fragment key={msg.message_id || index}>
                          {showDate && (
                            <div className="chat-date-divider">
                              {msg.timestampDate.toLocaleDateString("ko-KR", { month: "numeric", day: "numeric" })}
                            </div>
                          )}
                          <div className={`chat-message ${msg.user_id === userId ? "mine" : "other"}`}>
                            {msg.user_id !== userId && <div className="chat-username">{msg.username}</div>}
                            <div className="chat-bubble">{msg.message}</div>
                            <span className="chat-timestamp">{formatTime(msg.timestampDate)}</span>
                          </div>
                        </React.Fragment>
                      );
                    })}
                  </div>
                  {/* 메시지 입력창 */}
                  <div className="chat-input">
                    <input
                      type="text"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey && !isComposing(e)) {
                          e.preventDefault(); 
                          sendMessage();
                        }
                      }}
                    />
                    <button type="button" onClick={sendMessage}>전송</button>
                  </div>
                </div>

                {/* 우측: 프로젝트/DM 탭 구분 목록 */}
                <ChatList
                  setSelectedProjectId={setSelectedProjectId}
                  selectedProjectId={selectedProjectId}
                  activeTab={activeTab}
                  setActiveTab={setActiveTab}
                  setSelectedDmRoomId={setSelectedDmRoomId}
                  setDmPartnerName={setDmPartnerName}
                  selectedDmRoomId={selectedDmRoomId}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
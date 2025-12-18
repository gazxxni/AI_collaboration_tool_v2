import React, { useState, useEffect } from "react";
import "./ChatList.css"; 

const ChatList = ({
  setSelectedProjectId,
  selectedProjectId,
  activeTab,             
  setActiveTab,          
  selectedDmRoomId,      
  setSelectedDmRoomId,   
  setDmPartnerName       
}) => {
  const [userId, setUserId] = useState(null);
  const [projectList, setProjectList] = useState([]);
  const [dmRooms, setDmRooms] = useState([]); 

  // 사용자 정보 가져오기
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/users/name/", {
      method: "GET",
      credentials: "include"
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.user_id) {
          setUserId(parseInt(data.user_id));
        }
      })
      .catch((err) => console.error("🚨 사용자 정보를 불러오지 못했습니다.", err));
  }, []);

  // 프로젝트 목록 불러오기 (chat/ 제거)
  useEffect(() => {
    if (!userId) return;

    const fetchProjects = () => {
      // ✅ 수정됨: /chat/api/... -> /api/projects/...
      fetch(`http://127.0.0.1:8000/api/projects/${userId}/`)
        .then((res) => res.json())
        .then((data) => {
          if (!data.projects) {
            console.log("프로젝트 목록이 없습니다.");
            return;
          }
          const sorted = [...data.projects].sort((a, b) => {
            const tA = a.latest_message_time ? new Date(a.latest_message_time).getTime() : 0;
            const tB = b.latest_message_time ? new Date(b.latest_message_time).getTime() : 0;
            return tB - tA;
          });
          setProjectList(sorted);
        })
        .catch((err) => console.error("🚨 프로젝트 목록 오류:", err));
    };

    fetchProjects();
    const intervalId = setInterval(fetchProjects, 10000);
    return () => clearInterval(intervalId);
  }, [userId]);

  // DM 방 목록 불러오기 (chat/ 제거)
  useEffect(() => {
    if (!userId) return;

    // ✅ 수정됨: /chat/api/... -> /api/dm_rooms/...
    fetch(`http://127.0.0.1:8000/api/dm_rooms/${userId}/`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.dm_rooms) {
          console.log("DM 방이 없습니다.");
          return;
        }
        const sorted = [...data.dm_rooms].sort((a, b) => {
          const tA = a.latest_message_time_iso ? new Date(a.latest_message_time_iso).getTime() : 0;
          const tB = b.latest_message_time_iso ? new Date(b.latest_message_time_iso).getTime() : 0;
          return tB - tA;
        });
        setDmRooms(sorted);
      })
      .catch((err) => console.error("🚨 DM 목록 오류:", err));
  }, [userId]);

  return (
    <div className="chatlist-container">
      {/* 탭 헤더 */}
      <div className="chatlist-header">
        <button
          className={`tab-button ${activeTab === "project" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("project");
            setSelectedDmRoomId(null);
          }}
        >
          프로젝트
        </button>
        <button
          className={`tab-button ${activeTab === "dm" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("dm");
            setSelectedProjectId(null);
          }}
        >
          개인 채팅
        </button>
      </div>

      <span className="chatlist-text">정렬 기준 : 최신</span>

      {/* 목록 렌더링 */}
      {activeTab === "project" ? (
        <ul className="chat-list">
          {projectList.map((project) => (
            <li
              key={project.project_id}
              onClick={() => setSelectedProjectId(project.project_id)}
              className={selectedProjectId === project.project_id ? "selected" : ""}
            >
              {project.project_name}
            </li>
          ))}
        </ul>
      ) : (
        <ul className="chat-list">
          {dmRooms.map((room) => (
            <li
              key={room.room_id}
              onClick={() => {
                setSelectedDmRoomId(room.room_id);
                setDmPartnerName(room.partner_name);
              }}
              className={selectedDmRoomId === room.room_id ? "selected" : ""}
            >
              {room.partner_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ChatList;
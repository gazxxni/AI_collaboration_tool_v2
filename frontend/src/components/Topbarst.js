import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import api from "../api/axios"; // ✅ API 모듈 사용
import "./Topbarst.css";

function Topbarst() {
  // 라우트 파라미터에서 projectId 읽기
  const { projectId: routeProjectId } = useParams();

  // 상태 관리
  const [isStarred, setIsStarred] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectId, setProjectId] = useState(null);
  const [userId, setUserId] = useState("");
  
  // 이전 프로젝트 이름 저장 (로딩 중 깜빡임 방지)
  const previousProjectNameRef = useRef("");

  // 1) 사용자 정보 불러오기
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        // ✅ api 모듈 사용 (/api/users/name/)
        const res = await api.get("/api/users/name/");
        setUserId(res.data.user_id);
      } catch (error) {
        // console.error("사용자 정보 로드 실패", error);
      }
    };
    fetchUserData();
  }, []);

  // 2) 사용자 ID와 라우트 파라미터가 있으면 프로젝트 정보 찾기
  useEffect(() => {
    if (!userId || !routeProjectId) return;

    const fetchProjectByRouteParam = async () => {
      try {
        // ✅ [수정됨] 올바른 경로: /api/users/{id}/projects/
        const res = await api.get(`/api/users/${userId}/projects/`);

        if (res.data && res.data.projects) {
          const matched = res.data.projects.find(
            (p) => p.project_id === Number(routeProjectId)
          );
          
          if (matched) {
            setProjectId(matched.project_id);
            setProjectName(matched.project_name || "");
            setIsStarred(matched.is_favorite);
          }
        }
      } catch (err) {
        console.error("프로젝트 목록 불러오기 실패:", err);
      }
    };

    fetchProjectByRouteParam();
  }, [userId, routeProjectId]);

  // 3) 프로젝트 이름 변경 시 ref 업데이트
  useEffect(() => {
    if (projectName) {
      previousProjectNameRef.current = projectName;
    }
  }, [projectName]);

  // 즐겨찾기 토글
  const handleFavoriteToggle = async () => {
    if (!projectId) return;
    
    try {
      // ✅ [수정됨] 올바른 경로: /api/users/{uid}/favorites/{pid}/
      const url = `/api/users/${userId}/favorites/${projectId}/`;
      const method = isStarred ? "delete" : "post";

      // api 모듈로 동적 메서드 호출
      await api({ method, url });

      setIsStarred(!isStarred);
    } catch (error) {
      console.error("Error toggling favorite:", error);
      alert("즐겨찾기 변경 실패");
    }
  };

  const handleListClick = () => {
    console.log("프로젝트 리스트 클릭");
  };

  const displayedProjectName = projectName || previousProjectNameRef.current;

  return (
    <header className="Topbarst_header">
      <div className="Topbarst_profile_button"></div>
      <div
        className={`Topbarst_profile_starbutton ${isStarred ? "starred" : ""}`}
        onClick={handleFavoriteToggle}
      />
      <img
        className="Topbarst_listlogo"
        alt="listlogo"
        src="/listlogo.jpg"
        onClick={handleListClick}
      />
      <h1>{displayedProjectName}</h1>
    </header>
  );
}

export default Topbarst;
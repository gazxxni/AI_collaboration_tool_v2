import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Login from './pages/Login';
import MainPage from './pages/MainPage';
import Calendar from './pages/Calendar';
import ProjectCreation from './pages/ProjectCreation';
import Header from './components/Header';
import Invite from './pages/Invite';
import Minutes from "./pages/Minutes";
import Report from "./pages/Report";
import Chat from "./pages/Chat";
import ProjectDetail from './pages/ProjectDetail';
import Profile from './pages/Profile';
import TaskPage from './pages/TaskPage';
import Files from './pages/Files';
import ProjectCalendar from './pages/ProjectCalendar';
import ProjectFile from './pages/ProjectFile';
import ProjectActivity from './pages/ProjectActivity';
import TeamFinder from './pages/TeamFinder';
import ScrollToTop from './components/ScrollToTop';
import api from './api/axios'; // ✅ 생성한 axios 모듈 import

// [추가] Toast 관련 임포트 (전역 설정용)
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

function AppContent() {
  const location = useLocation();
  const [userName, setUserName] = useState("");
  const [userId, setUserId] = useState(null);
  const [currentProjectId, setCurrentProjectId] = useState(null);

  // 1) 사용자 정보 호출 (메인 및 특정 경로에서만)
  useEffect(() => {
    const path = location.pathname;
    if (path === "/") return;
    // 정규식 테스트 또는 메인 페이지일 때 실행
    if (path !== "/main" && !/^\/project\/\d+\/task$/.test(path)) return;

    const fetchUserData = async () => {
      try {
        // ✅ axios 모듈 사용
        const response = await api.get("/api/users/name/");
        setUserName(response.data.name);
        setUserId(response.data.user_id);
      } catch (error) {
        console.error("사용자 정보 로드 실패:", error);
      }
    };
    fetchUserData();
  }, [location.pathname]);

  // 2) 현재 프로젝트 정보 호출
  useEffect(() => {
    if (!userId) return;

    // URL이 /project/... 형태라면 전역 프로젝트 ID를 덮어쓰지 않음
    if (location.pathname.startsWith("/project/")) {
      return;
    }

    const fetchProjectData = async () => {
      try {
        // ✅ [수정됨] 올바른 경로: /api/users/projects/get/
        const res = await api.get("/api/users/projects/get/");
        if (res.data && res.data.project_id) {
          setCurrentProjectId(res.data.project_id);
        }
      } catch (error) {
        // 404 등 에러가 나도 콘솔에만 찍고 넘어감 (아직 선택된 프로젝트가 없을 수 있음)
        console.error("프로젝트 정보를 가져오는 데 실패했습니다.", error);
      }
    };
    fetchProjectData();
  }, [userId, location.pathname]);

  const userInitials = userName ? userName.slice(-2) : "";

  // 특정 페이지에서는 헤더를 숨김
  const hideHeaderOnRoutes = ["/", "/Invite", "/Chat", "/profile"];
  const showHeader = !hideHeaderOnRoutes.includes(location.pathname);

  return (
    <>
      {/* [추가] 전역 알림 컨테이너 (페이지 이동 후에도 알림 유지) */}
      <ToastContainer
        position="bottom-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick={false} // 클릭 시 이동 이벤트를 위해 false로 설정 (ProjectCreation.js에서 개별 제어)
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />

      {showHeader && (
        <Header
          nameInitials={userInitials}
          currentProjectId={currentProjectId}
        />
      )}
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/main" element={<MainPage userId={userId} userName={userName} nameInitials={userInitials} />} />
        
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/team-finder" element={<TeamFinder />} />
        <Route
          path="/create-project"
          element={<ProjectCreation nameInitials={userInitials} />}
        />
        <Route path="/invite" element={<Invite />} />
        <Route path="/chat" element={<Chat />} />
        <Route
          path="/project-detail"
          element={<ProjectDetail nameInitials={userInitials} />}
        />
        <Route path="/profile" element={<Profile />} />
        <Route path="/files" element={<Files />} />
        
        {/* 프로젝트 하위 페이지들 */}
        <Route
          path="/project/:projectId/minutes"
          element={<Minutes nameInitials={userInitials} />}
        />
        <Route
          path="/project/:projectId/report"
          element={<Report nameInitials={userInitials} />}
        />
        <Route
          path="/project/:projectId/task"
          element={<TaskPage nameInitials={userInitials} />}
        />
        <Route
          path="/project/:projectId/file"
          element={<ProjectFile nameInitials={userInitials} />}
        />
        <Route
          path="/project/:projectId/calendar"
          element={<ProjectCalendar />}
        />
        <Route
          path="/project/:projectId/activity"
          element={<ProjectActivity />}
        />
      </Routes>
    </>
  );
}

export default App;
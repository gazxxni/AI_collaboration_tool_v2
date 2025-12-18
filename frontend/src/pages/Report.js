/* eslint-disable */
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { Editor } from '@tinymce/tinymce-react';
import './Report.css';
import Header from '../components/Header';
import Topbar from "../components/Topbar";
import Topbarst from '../components/Topbarst';
import { FaRobot, FaSave, FaEdit, FaTrash, FaFileWord, FaTimes, FaToggleOn, FaToggleOff, FaFileAlt } from 'react-icons/fa';

// Toast 알림 임포트
import { toast } from 'react-toastify';

function Report({ nameInitials, currentProjectId }) {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const editorRef = useRef(null);
  const savedSectionRef = useRef(null);

  // 사용자 정보
  const [userId, setUserId] = useState(null);

  // 보고서 작성 상태
  const [reportType, setReportType] = useState("주간보고서"); 
  const [summaryHTML, setSummaryHTML] = useState("");

  // 저장된 보고서 목록
  const [savedReports, setSavedReports] = useState([]);

  // 로딩 상태
  const [loading, setLoading] = useState(false);
  const [isAutoWeekly, setIsAutoWeekly] = useState(false);

  // 모달 상태
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingReport, setEditingReport] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [viewContent, setViewContent] = useState("");

  // 1) 사용자 정보 가져오기
  const fetchUserInfo = async () => {
    try {
      const response = await axios.get("http://127.0.0.1:8000/api/users/name/", { withCredentials: true });
      if (response.data && response.data.user_id) {
          console.log("✅ [Front] User ID:", response.data.user_id);
          setUserId(response.data.user_id);
          return response.data.user_id;
      }
    } catch (error) {
      console.error("❌ [Front] User Info Error:", error);
    }
    return null;
  };

  useEffect(() => { fetchUserInfo(); }, []);

  // 2) 보고서 목록 불러오기 (isMounted 제거 - 무조건 실행)
  const fetchSavedReports = async () => {
    try {
      console.log(`📡 [Front] 목록 요청: Project ${projectId}`);
      const timestamp = new Date().getTime();
      const response = await axios.get(
          `http://127.0.0.1:8000/gptapi/report/${projectId || 1}/?t=${timestamp}`,
          { withCredentials: true }
      );
      
      // 안전장치 없이 무조건 상태 업데이트 (디버깅용)
      if (response.data && response.data.reports) {
          console.log("📦 [Front] 목록 수신:", response.data.reports.length, "개");
          setSavedReports(response.data.reports);
      } else {
          console.warn("⚠️ [Front] 목록 데이터 없음");
      }
    } catch (error) {
      console.error("❌ [Front] 목록 불러오기 실패:", error);
    }
  };

  useEffect(() => {
    if (projectId) fetchSavedReports();
  }, [projectId]);

  // ✅ 3) AI 요약 -> 저장 -> 새로고침 (강력한 버전)
  const handleAISummaryAndSave = async (targetType) => {
    setLoading(true);

    let currentUserId = userId;
    if (!currentUserId) currentUserId = await fetchUserInfo();

    if (!currentUserId) {
        setLoading(false);
        toast.error("로그인 정보가 없습니다.");
        return;
    }

    const endpoint = targetType === "최종보고서" ? "summarize-finalreport" : "summarize-report";
    const toastId = toast.loading(`AI가 ${targetType}를 생성 중입니다...`, { closeButton: false });

    try {
      const today = new Date().toISOString().split("T")[0];
      
      // [1] 생성
      const genResponse = await axios.post(
        `http://127.0.0.1:8000/gptapi/${endpoint}/`, 
        { 
            project_id: parseInt(projectId),
            today,
            start_date: "2025-05-01", 
            end_date: "2025-05-07"
        },
        { withCredentials: true }
      );
      
      const generatedHTML = genResponse.data.summary;
      
      // 토스트 메시지 변경
      toast.update(toastId, { render: "생성 완료! 저장 중..." });

      // [2] 저장
      await axios.post(
        "http://127.0.0.1:8000/gptapi/report/save/",
        {
          title: targetType, 
          content: generatedHTML,
          user_id: parseInt(currentUserId),
          project_id: parseInt(projectId),
        },
        { withCredentials: true }
      );

      // [3] 즉시 목록 갱신 시도
      await fetchSavedReports();

      // [4] 완료 알림 (기존 토스트 닫고 새로운 클릭 전용 토스트 띄움)
      toast.dismiss(toastId);
      
      toast.success(
        <div style={{ cursor: 'pointer', padding: '10px' }}>
            <h4 style={{ margin: 0, fontWeight: 'bold' }}>🎉 저장 완료!</h4>
            <p style={{ margin: '5px 0 0 0', fontSize: '14px', textDecoration: 'underline' }}>
                여기를 클릭해 페이지 새로고침
            </p>
        </div>, 
        {
            autoClose: false, // X 누를 때까지 유지
            closeButton: true,
            closeOnClick: false, // 내용 클릭 시 닫히지 않고 onClick 이벤트 실행
            onClick: () => {
              navigate(`/project/${projectId}/report`);
              toast.dismiss();
          }
        }
      );

    } catch (error) {
      console.error("작업 실패:", error);
      toast.dismiss(toastId);
      toast.error("작업 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  // CRUD 함수들
  const handleUpdateReport = async () => {
    try {
      await axios.post(
        `http://127.0.0.1:8000/gptapi/report/update/${editingReport.report_id}/`,
        { title: editTitle, content: editContent },
        { withCredentials: true }
      );
      await fetchSavedReports();
      setIsEditModalOpen(false);
      toast.success("수정되었습니다.");
    } catch (err) { toast.error("수정 실패"); }
  };

  const handleDeleteReport = async (report) => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    try {
      await axios.delete(
        `http://127.0.0.1:8000/gptapi/report/delete/${report.report_id}/`,
        { withCredentials: true }
      );
      setSavedReports(prev => prev.filter(r => r.report_id !== report.report_id));
      toast.success("삭제되었습니다.");
    } catch (err) { toast.error("삭제 실패"); }
  };

  const handleExportDocx = async (report) => {
    try {
      const res = await axios.get(
        `http://127.0.0.1:8000/gptapi/report/html2docx/${report.report_id}/`,
        { responseType: 'blob', withCredentials: true }
      );
      const blob = new Blob([res.data], { type: res.headers['content-type'] });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${report.title}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) { toast.error("다운로드 실패"); }
  };

  const handleEditClick = (report) => {
    setEditingReport(report);
    setEditTitle(report.title);
    setEditContent(report.content);
    setIsEditModalOpen(true);
  };

  const handleViewClick = (content) => {
    setViewContent(content);
    setIsViewModalOpen(true);
  };

  const toggleAutoWeekly = () => {
      const newState = !isAutoWeekly;
      setIsAutoWeekly(newState);
      toast.info(newState ? "주간 보고서 자동 ON" : "자동 생성 OFF");
  };

  return (
    <div className="Report_wrapper">
      <Header nameInitials={nameInitials} currentProjectId={currentProjectId} />
      <Topbarst />
      <Topbar />

      <div className="Report_container">
        <div className="Report_content">
          <div className="Report_controlPanel">
            <div className="Report_autoToggle">
                <span className="Report_toggleLabel">주간 보고서 자동 생성 (매주 일요일)</span>
                <button className="Report_toggleBtn" onClick={toggleAutoWeekly}>
                    {isAutoWeekly ? <FaToggleOn size={30} color="#4caf50"/> : <FaToggleOff size={30} color="#ccc"/>}
                </button>
            </div>
            <div className="Report_manualActions">
                <button className="Report_weeklyBtn" onClick={() => handleAISummaryAndSave("주간보고서")} disabled={loading}>
                    <FaRobot /> 금주 주간보고서 즉시 생성
                </button>
                <button className="Report_finalBtn" onClick={() => handleAISummaryAndSave("최종보고서")} disabled={loading}>
                    <FaFileAlt /> 최종보고서 생성
                </button>
            </div>
          </div>

          <div className="Report_savedSection" ref={savedSectionRef}>
            {savedReports.length > 0 ? (
              <>
                <h2 className="Report_sectionTitle">저장된 보고서 목록</h2>
                <div className="Report_savedList">
                  {savedReports.map((report, idx) => (
                    <div key={idx} className="Report_savedCard">
                      <div className="Report_savedHeader">
                        <h3>{report.title}</h3>
                        <span className="Report_savedDate">
                          {new Date(report.created_date).toLocaleDateString('ko-KR')}
                        </span>
                      </div>
                      <div className="Report_savedContent" onClick={() => handleViewClick(report.content)} dangerouslySetInnerHTML={{ __html: report.content }} />
                      <div className="Report_savedActions">
                        <button className="Report_wordBtn" onClick={() => handleExportDocx(report)}><FaFileWord /> Word</button>
                        <button className="Report_editBtn" onClick={() => handleEditClick(report)}><FaEdit /> 수정</button>
                        <button className="Report_deleteBtn" onClick={() => handleDeleteReport(report)}><FaTrash /> 삭제</button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', marginTop: '50px', color: '#888' }}>
                  <p>아직 작성된 보고서가 없습니다. 생성 버튼을 눌러보세요.</p>
              </div>
            )}
          </div>

          {isEditModalOpen && (
            <div className="Report_modal" onClick={() => setIsEditModalOpen(false)}>
              <div className="Report_modalContent" onClick={(e) => e.stopPropagation()}>
                <div className="Report_modalHeader">
                  <h3>보고서 수정</h3>
                  <button className="Report_modalClose" onClick={() => setIsEditModalOpen(false)}><FaTimes /></button>
                </div>
                <div className="Report_modalBody">
                  <select className="Report_typeSelect" value={editTitle} onChange={e => setEditTitle(e.target.value)}>
                    <option value="주간보고서">주간보고서</option>
                    <option value="최종보고서">최종보고서</option>
                  </select>
                  <Editor
                    tinymceScriptSrc="/tinymce/tinymce.min.js"
                    value={editContent}
                    licenseKey='gpl'
                    init={{ height: 400, language: 'ko_KR', menubar: true }}
                    onEditorChange={newContent => setEditContent(newContent)}
                  />
                </div>
                <div className="Report_modalFooter">
                  <button className="Report_saveBtn" onClick={handleUpdateReport}><FaSave /> 저장하기</button>
                  <button className="Report_cancelBtn" onClick={() => setIsEditModalOpen(false)}>취소</button>
                </div>
              </div>
            </div>
          )}

          {isViewModalOpen && (
            <div className="Report_modal" onClick={() => setIsViewModalOpen(false)}>
              <div className="Report_modalContent" onClick={e => e.stopPropagation()}>
                <div className="Report_modalHeader">
                  <h3>보고서 내용 보기</h3>
                  <button className="Report_modalClose" onClick={() => setIsViewModalOpen(false)}><FaTimes /></button>
                </div>
                <div className="Report_modalBody">
                  <div dangerouslySetInnerHTML={{ __html: viewContent }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>  
    </div>
  );
}

export default Report;
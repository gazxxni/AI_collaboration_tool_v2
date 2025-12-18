import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom'; // useNavigate 추가
import { Editor } from '@tinymce/tinymce-react';
import './Minutes.css';
import Header from '../components/Header';
import Topbar from "../components/Topbar";
import Topbarst from '../components/Topbarst';
import MinutesUploadModal from '../components/MinutesUploadModal';
import { FaMicrophone, FaFileAudio, FaRobot, FaSave, FaEdit, FaTrash, FaFileWord, FaTimes, FaTasks } from 'react-icons/fa';

// Toast 알림 임포트
import { toast } from 'react-toastify';

function Minutes({nameInitials, currentProjectId}) {
  const { projectId } = useParams();
  const editorRef = useRef(null);
  const navigate = useNavigate(); // 네비게이션 훅

  // 사용자 정보
  const [userName, setUserName] = useState("");
  const [userId, setUserId] = useState("");

  // 회의록 작성 상태
  const [minutesTitle, setMinutesTitle] = useState("");
  const [minutesContent, setMinutesContent] = useState("");
  
  // 저장된 회의록 목록
  const [savedMinutes, setSavedMinutes] = useState([]);

  // 로딩 상태
  const [loading, setLoading] = useState(false);

  // 수정 모달
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingMinute, setEditingMinute] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");

  // STT용 상태
  const [audioFile, setAudioFile] = useState(null);
  const [transcript, setTranscript] = useState("");

  // 보기 모달
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [viewContent, setViewContent] = useState("");

  // AI 업무 추출 모달
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [selectedMinuteForTask, setSelectedMinuteForTask] = useState(null);

  // 1) 사용자 정보 가져오기
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await axios.get("http://127.0.0.1:8000/api/users/name/", { withCredentials: true });
        setUserName(response.data.name);
        setUserId(response.data.user_id);
      } catch (error) {
        console.error("사용자 정보를 가져오는 데 실패했습니다:", error);
      }
    };
    fetchUserInfo();
  }, []);

  // 2) 회의록 목록 불러오기
  const fetchSavedMinutes = async () => {
    try {
      // 캐싱 방지용 타임스탬프 추가
      const timestamp = new Date().getTime();
      const response = await axios.get(`http://127.0.0.1:8000/api/users/minutes/${projectId}/?t=${timestamp}`);
      setSavedMinutes(response.data.minutes);
    } catch (error) {
      console.error("저장된 회의록 목록 불러오기 실패:", error);
    }
  };

  useEffect(() => {
    if (projectId) {
        fetchSavedMinutes();
    }
  }, [projectId]);

  // 파일 선택 핸들러
  const handleFileChange = e => {
    setAudioFile(e.target.files[0]);
  };

  // STT 요청 핸들러
  const handleSTT = async () => {
    if (!audioFile) {
      return toast.warning("오디오 파일을 선택하세요.");
    }
    
    const toastId = toast.loading("음성을 텍스트로 변환하고 있습니다...");
    setLoading(true);

    const fd = new FormData();
    fd.append("audio", audioFile);
    
    try {
      const res = await axios.post(
        "http://127.0.0.1:8000/gptapi/transcribe/",
        fd,
        {
          withCredentials: true,
          headers: { "Content-Type": "multipart/form-data" }
        }
      );
      const text = res.data.transcript || "";
      setTranscript(text);
      if (editorRef.current) {
        editorRef.current.setContent(text);
      }
      
      toast.update(toastId, {
        render: "변환이 완료되었습니다.",
        type: "success",
        isLoading: false,
        autoClose: 3000
      });

    } catch (err) {
      console.error("STT 요청 실패:", err);
      toast.update(toastId, {
        render: "변환에 실패했습니다.",
        type: "error",
        isLoading: false,
        autoClose: 3000
      });
    }
    setLoading(false);
  };

  // ✅ 3) AI 요약 및 "자동 저장" (수정됨: 클릭 시 페이지 새로고침/이동)
  const handleAISummaryAndSave = async () => {
    const content = editorRef.current ? editorRef.current.getContent() : "";
    if (!minutesTitle || !content) {
      toast.warning("회의 제목과 내용을 입력하세요.");
      return;
    }

    // 1. 알림 시작
    const toastId = toast.loading("AI가 회의록을 요약하고 저장 중입니다...");
    setLoading(true);

    try {
      // 2. 요약 요청 (Async)
      const summaryRes = await axios.post(
        "http://127.0.0.1:8000/gptapi/summarize/",
        { notes: content }
      );
      
      const summaryHTML = summaryRes.data.summary_html;

      // 3. 자동 저장 요청
      await axios.post(
        "http://127.0.0.1:8000/api/users/minutes/save/",
        {
          title: minutesTitle,
          content: summaryHTML,
          user_id: userId,
          project_id: projectId,
        }
      );

      // 4. 목록 갱신
      await fetchSavedMinutes();

      // 5. 입력창 초기화
      setMinutesTitle("");
      setMinutesContent("");
      if (editorRef.current) editorRef.current.setContent("");

      // 6. 성공 알림 (HTML div 클릭 시 페이지 이동/새로고침)
      toast.update(toastId, {
        render: (
            <div 
                style={{ cursor: 'pointer' }}
                onClick={() => {
                    // 모달을 띄우는 대신 페이지를 새로고침하여 목록을 확실히 보여줌
                    // (또는 navigate로 이동 처리)
                    window.location.reload(); 
                }}
            >
                🎉 요약 및 저장이 완료되었습니다!<br/>
                <span style={{ fontSize: '0.85em', textDecoration: 'underline', color: '#4caf50' }}>
                    (여기를 눌러 확인하세요)
                </span>
            </div>
        ),
        type: "success",
        isLoading: false,
        autoClose: false,
        closeOnClick: true, // 클릭 시 닫히면서 onClick 이벤트 실행
        closeButton: true   // 닫기 버튼 표시
      });

    } catch (error) {
      console.error("AI 요약/저장 실패:", error);
      
      let errorMsg = "요약 및 저장에 실패했습니다.";
      if (error.response?.status === 400 && error.response.data?.invalid) {
          errorMsg = "내용이 부족하여 요약할 수 없습니다.";
      }

      toast.update(toastId, {
        render: errorMsg,
        type: "error",
        isLoading: false,
        autoClose: 5000,
        closeButton: true
      });
    } finally {
      setLoading(false);
    }
  };

  // 4) 일반 저장
  const handleManualSave = async () => {
    const content = editorRef.current ? editorRef.current.getContent() : "";
    if (!minutesTitle || !content) {
      toast.warning("제목과 내용을 입력하세요.");
      return;
    }
    try {
      await axios.post(
        "http://127.0.0.1:8000/api/users/minutes/save/",
        {
          title: minutesTitle,
          content: content,
          user_id: userId,
          project_id: projectId,
        }
      );
      toast.success("회의록이 저장되었습니다.");
      setMinutesTitle("");
      if (editorRef.current) editorRef.current.setContent("");
      
      // 목록 갱신
      await fetchSavedMinutes();

    } catch (error) {
      console.error("회의록 저장 실패:", error);
      toast.error("저장에 실패했습니다.");
    }
  };

  // 5) 수정 저장
  const handleUpdateMinutes = async () => {
    try {
      await axios.post(
        `http://127.0.0.1:8000/api/users/minutes/update/${editingMinute.minutes_id}/`,
        { title: editTitle, content: editContent }
      );
      await fetchSavedMinutes();
      setIsEditModalOpen(false);
      toast.success("수정되었습니다.");
    } catch (err) {
      console.error("수정 실패:", err);
      toast.error("수정에 실패했습니다.");
    }
  };

  // 6) 삭제
  const handleDeleteClick = async (minute) => {
    if (!window.confirm("정말 삭제하시겠습니까?")) return;
    try {
      await axios.delete(
        `http://127.0.0.1:8000/api/users/minutes/delete/${minute.minutes_id}/`
      );
      setSavedMinutes(savedMinutes.filter(m => m.minutes_id !== minute.minutes_id));
      toast.success("삭제되었습니다.");
    } catch (err) {
      console.error("삭제 실패:", err);
      toast.error("삭제에 실패했습니다.");
    }
  };

  // 7) Word 저장
  const handleExportDocx = async (minute) => {
    try {
      const res = await axios.get(
        `http://127.0.0.1:8000/api/users/minutes/html2docx/${minute.minutes_id}/`,
        { responseType: 'blob', withCredentials: true }
      );
      const blob = new Blob([res.data], { type: res.headers['content-type'] });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${minute.title}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("회의록 DOCX 다운로드 실패:", err);
      toast.error("다운로드에 실패했습니다.");
    }
  };

  // 편집 버튼 클릭
  const handleEditClick = (minute) => {
    setEditingMinute(minute);
    setEditTitle(minute.title);
    setEditContent(minute.content);
    setIsEditModalOpen(true);
  };

  // 보기 모달 열기 함수
  const handleViewClick = (content) => {
    setViewContent(content);
    setIsViewModalOpen(true);
  };

  // AI 업무 생성 버튼 클릭
  const handleCreateTasksFromMinute = (minute) => {
    setSelectedMinuteForTask(minute);
    setShowTaskModal(true);
  };

  return (
    <div className="Minutes_wrapper">
      <Header 
        nameInitials={nameInitials}
        currentProjectId={currentProjectId}
      />
      <Topbarst />
      <Topbar />

      <div className="Minutes_container">
        <div className="Minutes_content">
          <div className="Minutes_editorCard">
            <input
              className="Minutes_titleInput"
              type="text"
              placeholder="회의 제목을 입력하세요..."
              value={minutesTitle}
              onChange={e => setMinutesTitle(e.target.value)}
            />

            <div className="Minutes_audioSection">
              <label className="Minutes_fileLabel">
                <FaFileAudio />
                <input type="file" accept="audio/*" onChange={handleFileChange} />
                {audioFile ? audioFile.name : "오디오 파일 선택"}
              </label>
              <button 
                className="Minutes_sttBtn" 
                onClick={handleSTT} 
                disabled={loading || !audioFile}
                style={{ cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
              >
                {loading ? "변환 중..." : "음성을 텍스트로"}
              </button>
            </div>

            <div className="Minutes_editorWrapper">
              <Editor
                tinymceScriptSrc="/tinymce/tinymce.min.js"
                initialValue={minutesContent || transcript}
                licenseKey='gpl'
                init={{
                  height: 400,
                  language: 'ko_KR',
                  menubar: true,
                  plugins: [
                    'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
                    'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                    'insertdatetime', 'table', 'preview', 'help', 'wordcount'
                  ],
                  toolbar:
                    'undo redo | formatselect fontselect fontsizeselect | bold italic backcolor | ' +
                    'alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | ' +
                    'table | removeformat | help',
                  skin: 'oxide',
                  content_css: 'default'
                }}
                onInit={(_evt, editor) => editorRef.current = editor}
              />
            </div>

            <div className="Minutes_actions">
              {/* AI 요약 및 저장 버튼 */}
              <button 
                className="Minutes_aiBtn" 
                onClick={handleAISummaryAndSave} 
                disabled={loading}
                style={{ cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
              >
                <FaRobot />
                {loading ? "처리 중..." : "AI 요약 및 저장"}
              </button>
              
              {/* 일반 저장 버튼 */}
              <button className="Minutes_saveBtn" onClick={handleManualSave}>
                <FaSave />
                그냥 저장
              </button>
            </div>
          </div>

          {savedMinutes.length > 0 && (
            <div className="Minutes_savedSection">
              <h2 className="Minutes_sectionTitle">
                저장된 회의록
              </h2>
              <div className="Minutes_savedList">
                {savedMinutes.map((minute, idx) => (
                  <div key={idx} className="Minutes_savedCard">
                    <div className="Minutes_savedHeader">
                      <h3>{minute.title}</h3>
                      <span className="Minutes_savedDate">
                        {new Date(minute.created_date).toLocaleDateString('ko-KR')}
                      </span>
                    </div>
                    <div 
                      className="Minutes_savedContent"
                      onClick={() => handleViewClick(minute.content)}
                      dangerouslySetInnerHTML={{ __html: minute.content }}
                    />
                    <div className="Minutes_savedActions">
                      <button 
                        className="Minutes_taskBtn" 
                        onClick={() => handleCreateTasksFromMinute(minute)}
                        title="회의록에서 업무 자동 생성"
                      >
                        <FaTasks /> 업무 생성
                      </button>
                      <button 
                        className="Minutes_wordBtn" 
                        onClick={() => handleExportDocx(minute)}
                      >
                        <FaFileWord /> Word
                      </button>
                      <button 
                        className="Minutes_editBtn" 
                        onClick={() => handleEditClick(minute)}
                      >
                        <FaEdit /> 수정
                      </button>
                      <button 
                        className="Minutes_deleteBtn" 
                        onClick={() => handleDeleteClick(minute)}
                      >
                        <FaTrash /> 삭제
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 수정 모달 */}
          {isEditModalOpen && (
            <div className="Minutes_modal" onClick={() => setIsEditModalOpen(false)}>
              <div className="Minutes_modalContent" onClick={(e) => e.stopPropagation()}>
                <div className="Minutes_modalHeader">
                  <h3>회의록 수정</h3>
                  <button 
                    className="Minutes_modalClose" 
                    onClick={() => setIsEditModalOpen(false)}
                  >
                    <FaTimes />
                  </button>
                </div>
                <div className="Minutes_modalBody">
                  <input
                    className="Minutes_titleInput"
                    type="text"
                    value={editTitle}
                    onChange={e => setEditTitle(e.target.value)}
                  />
                  <Editor
                    tinymceScriptSrc="/tinymce/tinymce.min.js"
                    value={editContent}
                    licenseKey='gpl'
                    init={{
                      height: 400,
                      language: 'ko_KR',
                      menubar: true,
                      plugins: [
                        'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
                        'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                        'insertdatetime', 'table', 'preview', 'help', 'wordcount'
                      ],
                      toolbar:
                        'undo redo | formatselect fontselect fontsizeselect | bold italic backcolor | ' +
                        'alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | ' +
                        'table | removeformat | help'
                    }}
                    onEditorChange={newContent => setEditContent(newContent)}
                  />
                </div>
                <div className="Minutes_modalFooter">
                  <button className="Minutes_saveBtn" onClick={handleUpdateMinutes}>
                    <FaSave /> 저장하기
                  </button>
                  <button 
                    className="Minutes_cancelBtn" 
                    onClick={() => setIsEditModalOpen(false)}
                  >
                    취소
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 보기 모달 (토스트 클릭 시 여기로 연결됨) */}
          {isViewModalOpen && (
            <div className="Minutes_modal" onClick={() => setIsViewModalOpen(false)}>
              <div
                className="Minutes_modalContent"
                onClick={e => e.stopPropagation()}
              >
                <div className="Minutes_modalHeader">
                  <h3>회의록 내용 보기</h3>
                  <button
                    className="Minutes_modalClose"
                    onClick={() => setIsViewModalOpen(false)}
                  >
                    <FaTimes />
                  </button>
                </div>
                <div className="Minutes_modalBody">
                  <div
                    dangerouslySetInnerHTML={{ __html: viewContent }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* AI 업무 추출 모달 */}
          {showTaskModal && selectedMinuteForTask && (
            <MinutesUploadModal
              projectId={projectId}
              minutesId={selectedMinuteForTask.minutes_id}
              initialContent={selectedMinuteForTask.content}
              userId={userId} // ✅ userId 전달 필수
              onClose={() => {
                setShowTaskModal(false);
                setSelectedMinuteForTask(null);
              }}
              onTasksCreated={() => {
                toast.success('업무가 생성되었습니다! 업무 페이지에서 확인하세요.', {autoClose: 5000});
                setShowTaskModal(false);
                setSelectedMinuteForTask(null);
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Minutes;
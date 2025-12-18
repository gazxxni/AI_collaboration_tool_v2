/* eslint-disable */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './MinutesUploadModal.css';

axios.defaults.withCredentials = true;

function MinutesUploadModal({ 
  projectId, 
  minutesId,
  initialContent,
  userId,  // ✅ props로 userId 받기
  onClose, 
  onTasksCreated 
}) {
  const [content, setContent] = useState(initialContent || '');
  const [loading, setLoading] = useState(false);
  const [extractedTasks, setExtractedTasks] = useState(null);
  const [error, setError] = useState('');
  
  useEffect(() => {
    if (initialContent) {
      setContent(initialContent);
    }
  }, [initialContent]);
  
  // AI 분석 실행
  const handleAnalyze = async () => {
    if (!content.trim()) {
      setError('회의록 내용을 입력하세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const requestBody = {
        project_id: projectId
      };
      
      if (minutesId) {
        requestBody.minutes_id = minutesId;
      } else {
        requestBody.content = content;
      }
      
      const response = await axios.post(
        'http://127.0.0.1:8000/gptapi/extract-tasks-from-minutes/',
        requestBody
      );
      
      console.log('✅ AI 분석 결과:', response.data);
      setExtractedTasks(response.data.tasks);
    } catch (error) {
      console.error('❌ AI 분석 실패:', error);
      setError(error.response?.data?.error || '업무 추출에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };
  
  // 업무 일괄 생성
  const handleCreateTasks = async () => {
    // ✅ props로 받은 userId 사용
    if (!userId) {
      setError('로그인 정보를 찾을 수 없습니다.');
      console.error('❌ userId가 없습니다:', userId);
      return;
    }
    
    console.log('✅ userId 확인:', userId);
    console.log('✅ projectId 확인:', projectId);
    
    setLoading(true);
    setError('');
    
    try {
      const requestData = {
        project_id: projectId,
        tasks: extractedTasks,
        user_id: userId // ✅ 수정된 부분
      };
      
      const response = await axios.post(
        'http://127.0.0.1:8000/gptapi/bulk-create-tasks-from-minutes/',
        requestData
      );
      
      console.log('✅ 업무 생성 완료:', response.data);
      alert(`${response.data.message}`);
      onTasksCreated(); // 부모 컴포넌트에 알림
      onClose();        // 모달 닫기
    } catch (error) {
      console.error('❌ 업무 생성 실패:', error);
      setError(error.response?.data?.error || '업무 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };
  
  // 업무 수정 핸들러
  const handleEditTask = (index, field, value) => {
    const updated = [...extractedTasks];
    updated[index][field] = value;
    setExtractedTasks(updated);
  };
  
  // 하위 업무 수정 핸들러
  const handleEditSubtask = (taskIndex, subtaskIndex, field, value) => {
    const updated = [...extractedTasks];
    updated[taskIndex].subtasks[subtaskIndex][field] = value;
    setExtractedTasks(updated);
  };
  
  // 업무 삭제
  const handleDeleteTask = (index) => {
    if (window.confirm('이 업무를 삭제하시겠습니까?')) {
      setExtractedTasks(extractedTasks.filter((_, i) => i !== index));
    }
  };
  
  // 하위 업무 삭제
  const handleDeleteSubtask = (taskIndex, subtaskIndex) => {
    const updated = [...extractedTasks];
    updated[taskIndex].subtasks = updated[taskIndex].subtasks.filter((_, i) => i !== subtaskIndex);
    setExtractedTasks(updated);
  };
  
  return (
    <div className="MinutesModal_overlay" onClick={onClose}>
      <div className="MinutesModal_content" onClick={(e) => e.stopPropagation()}>
        <button className="MinutesModal_closeBtn" onClick={onClose}>
          ✕
        </button>
        
        <h2 className="MinutesModal_title">
          🤖 AI 회의록 분석
        </h2>
        
        {error && (
          <div className="MinutesModal_error">
            ⚠️ {error}
          </div>
        )}
        
        {!extractedTasks ? (
          // Step 1: 회의록 입력
          <div className="MinutesModal_step1">
            <p className="MinutesModal_desc">
              회의록을 입력하면 AI가 자동으로 실행 가능한 업무를 추출합니다.
            </p>
            
            <textarea
              className="Minutes_textarea"
              placeholder="회의록 내용을 입력하세요..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={15}
              disabled={loading}
            />
            
            <div className="MinutesModal_buttons">
              <button 
                onClick={onClose} 
                disabled={loading}
                className="MinutesModal_cancelBtn"
              >
                취소
              </button>
              <button 
                onClick={handleAnalyze} 
                disabled={loading || !content.trim()}
                className="MinutesModal_primaryBtn"
              >
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    분석 중...
                  </>
                ) : (
                  '🔍 AI 분석 시작'
                )}
              </button>
            </div>
          </div>
        ) : (
          // Step 2: 추출된 업무 미리보기 및 수정
          <div className="MinutesModal_step2">
            <div className="Extracted_header">
              <h3>추출된 업무 ({extractedTasks.length}개)</h3>
              <p className="Extracted_subtitle">
                내용을 확인하고 수정한 후 생성 버튼을 눌러주세요.
              </p>
            </div>
            
            <div className="Extracted_tasks">
              {extractedTasks.map((task, index) => (
                <div key={index} className="Task_preview">
                  <div className="Task_preview_header">
                    <div className="Task_number">업무 {index + 1}</div>
                    <button 
                      className="Task_deleteBtn"
                      onClick={() => handleDeleteTask(index)}
                    >
                      🗑️ 삭제
                    </button>
                  </div>
                  
                  <div className="Task_edit_field">
                    <label>업무명</label>
                    <input
                      type="text"
                      value={task.task_name}
                      onChange={(e) => handleEditTask(index, 'task_name', e.target.value)}
                    />
                  </div>
                  
                  <div className="Task_edit_field">
                    <label>설명</label>
                    <textarea
                      value={task.description}
                      onChange={(e) => handleEditTask(index, 'description', e.target.value)}
                      rows={2}
                    />
                  </div>
                  
                  {/* 추가 필드들 (담당자, 날짜, 우선순위 등)은 UI 공간상 생략하거나 필요 시 추가 */}
                  
                  {/* 하위 업무 */}
                  {task.subtasks && task.subtasks.length > 0 && (
                    <div className="Subtasks">
                      <div className="Subtasks_header">
                        하위 업무 ({task.subtasks.length}개)
                      </div>
                      {task.subtasks.map((sub, subIndex) => (
                        <div key={subIndex} className="Subtask_item">
                          <div className="Subtask_header">
                            <span className="Subtask_label">└ 하위 {subIndex + 1}</span>
                            <button
                              className="Subtask_deleteBtn"
                              onClick={() => handleDeleteSubtask(index, subIndex)}
                            >
                              ✕
                            </button>
                          </div>
                          
                          <div className="Subtask_edit">
                            <input
                              type="text"
                              placeholder="업무명"
                              value={sub.task_name}
                              onChange={(e) => handleEditSubtask(index, subIndex, 'task_name', e.target.value)}
                            />
                            <input
                              type="text"
                              placeholder="담당자"
                              value={sub.assignee || ''}
                              onChange={(e) => handleEditSubtask(index, subIndex, 'assignee', e.target.value)}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
            
            <div className="MinutesModal_buttons">
              <button 
                onClick={() => {
                  setExtractedTasks(null);
                  setError('');
                }}
                disabled={loading}
                className="MinutesModal_cancelBtn"
              >
                ← 다시 분석
              </button>
              <button 
                onClick={handleCreateTasks}
                disabled={loading || extractedTasks.length === 0}
                className="MinutesModal_primaryBtn"
              >
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    생성 중...
                  </>
                ) : (
                  `✅ 업무 생성 (${extractedTasks.length}개)`
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MinutesUploadModal;
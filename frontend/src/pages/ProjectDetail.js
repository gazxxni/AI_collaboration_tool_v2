import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FaArrowLeft, FaSyncAlt } from 'react-icons/fa';
import axios from 'axios';
import './ProjectDetail.css';
import Loading from '../components/Loading'; // 필요없다면 삭제 또는 유지

function ProjectDetail() {
  const location = useLocation();
  const navigate = useNavigate();

  // ✅ location.state에서 값 추출
  const {
    projectName = '프로젝트 이름 미정',
    tasks: initialTasks = [],
    selectedUsers = [],
    start_date = "",
    end_date = "",
    project_description = "",
    project_goal = "",
    tech_stack = []
  } = location.state || {};

  const [editableProjectName, setEditableProjectName] = useState(projectName);
  const [projectId, setProjectId] = useState(null);
  const [tasks, setTasks] = useState(initialTasks);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    console.log("✅ ProjectDetail 로드됨");
    // ... 로그 생략 ...
  }, [projectName, tasks, selectedUsers, start_date, end_date]);

  // 프로젝트명 수정 핸들러
  const handleProjectNameChange = (newName) => {
    setEditableProjectName(newName);
  };

  // 상위 업무명 수정 핸들러
  const handleTaskNameChange = (taskIndex, newName) => {
    setTasks((prev) => {
      const newTasks = [...prev];
      newTasks[taskIndex] = {
        ...newTasks[taskIndex],
        "업무명": newName,
      };
      return newTasks;
    });
  };

  // 하위 업무명 수정 핸들러
  const handleSubTaskNameChange = (taskIndex, subIndex, newName) => {
    setTasks((prev) => {
      const newTasks = [...prev];
      if (Array.isArray(newTasks[taskIndex]["하위업무"])) {
        newTasks[taskIndex]["하위업무"][subIndex] = {
          ...newTasks[taskIndex]["하위업무"][subIndex],
          "업무명": newName,
        };
      }
      return newTasks;
    });
  };

  // 새로고침 버튼 (다시 생성하기)
  const handleRefresh = async () => {
    if (!projectName) return;
    setLoading(true);
    try {
      // [수정 1] URL 하이픈(-)으로 변경
      const response = await axios.post("http://127.0.0.1:8000/gptapi/generate-tasks/", {
        project_topic: projectName,
        project_description: project_description,
        project_goal: project_goal,
        tech_stack: tech_stack,
        selected_users: selectedUsers,
        project_start_date: start_date,
        project_end_date: end_date
      });
      if (response.data && response.data.tasks) {
        setTasks(response.data.tasks);
      } else {
        console.error("업무 생성 실패:", response.data.error);
      }
    } catch (error) {
      console.error("API 호출 오류:", error);
    }
    setLoading(false);
  };
  
  // 생성하기(최종 확정) 버튼
  const handleCreateDone = async () => {
    try {
      // [수정 2] URL 하이픈(-)으로 변경
      const response = await axios.post("http://127.0.0.1:8000/gptapi/confirm-tasks/", {
        project_name: editableProjectName,
        tasks: tasks,
        selected_users: selectedUsers,
        start_date: start_date,
        end_date: end_date
      });
  
      if (response.data && response.data.project_id) {
        const newProjectId = response.data.project_id;
        console.log("새 프로젝트 생성됨, ID =", newProjectId);

        // ✅ 새 프로젝트의 업무 페이지로 이동
        navigate(`/project/${newProjectId}/task`, {
          replace: true, 
        });
      } else {
        console.error("업무 저장 실패:", response.data.error);
        alert("업무 저장에 실패했습니다."); // 사용자 알림 추가
      }
    } catch (error) {
      console.error("API 호출 오류:", error);
      alert("서버와 통신 중 오류가 발생했습니다.");
    }
  };

  return (
    <div className="ProjectDetailPage">
      <div className="ProjectCard">
        <div className="CardHeader">
          <div className="CardBackButton" onClick={() => navigate('/main')}>
            <FaArrowLeft />
          </div>
          {/* 프로젝트명 인풋 */}
          <input 
            type="text" 
            className="CardTitleInput" 
            value={editableProjectName}
            onChange={(e) => handleProjectNameChange(e.target.value)}
          />
          <div className="CardRefreshButton" onClick={handleRefresh}>
            <FaSyncAlt />
          </div>
        </div>

        {loading && <Loading message="업무를 재생성하고 있습니다." />}
          <ul className="TaskList">
            {tasks.map((task, index) => {
              let parsedDesc = null;
              try {
                parsedDesc = JSON.parse(
                  typeof task.description === 'string'
                    ? task.description
                    : JSON.stringify(task)
                );
              } catch (error) {
                console.error("JSON 파싱 오류:", error);
              }

              const assignedUser = parsedDesc?.["배정된 사용자"] || "담당자 없음";
              const topTaskName = parsedDesc?.["업무명"] || task.task_name;
              const subTasks = parsedDesc?.["하위업무"] || [];
              const topStart = parsedDesc?.["시작일"];
              const topEnd = parsedDesc?.["종료일"];

              return (
                <li className="TaskItem" key={index}>
                  <span className="TaskStatus todo">{assignedUser}</span>
                  {/* 상위 업무 + 하위 업무를 세로로 쌓을 래퍼 */}
                  <div className="TaskDetailWrapper">
                    {/* 상위 업무 한 줄: 업무명 왼쪽, 날짜 오른쪽 */}
                    <div className="TaskContent">
                      <input
                        type="text"
                        className="TaskNameInput"
                        value={topTaskName}
                        onChange={(e) => handleTaskNameChange(index, e.target.value)}
                      />
                      {topStart && topEnd && (
                        <div className="TopDateRange">
                          {topStart} ~ {topEnd}
                        </div>
                      )}
                    </div>
                    {/* 하위 업무 리스트 */}
                    {Array.isArray(subTasks) && subTasks.length > 0 && (
                      <ul className="SubTaskList">
                        {subTasks.map((sub, subIdx) => (
                          <li key={subIdx} className="SubTaskItem">
                            <div className="SubTaskRow">
                              <span className="SubTaskStatus">
                                {sub["배정된 사용자"] || "담당자 없음"}
                              </span>
                              <input
                                type="text"
                                className="SubTaskNameInput"
                                value={sub["업무명"] || ""}
                                onChange={(e) => handleSubTaskNameChange(index, subIdx, e.target.value)}
                              />
                              {sub["요구 스킬"] && (
                                <span className="SubTaskSkill">
                                  (스킬: {sub["요구 스킬"].join(", ")})
                                </span>
                              )}
                              {sub["시작일"] && sub["종료일"] && (
                                <div className="SubTaskDateRange">
                                  {sub["시작일"]} ~ {sub["종료일"]}
                                </div>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        <div className="ButtonContainer">
          <button className="SubmitButton" onClick={handleCreateDone}>
            생성하기
          </button>
        </div>
      </div>
    </div>
  );
}

export default ProjectDetail;
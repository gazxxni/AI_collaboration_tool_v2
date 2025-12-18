/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import api from "../api/axios";
import { FaPlus, FaCaretRight, FaCaretDown } from "react-icons/fa";
import Topbar from "../components/Topbar";
import Topbarst from "../components/Topbarst";
import TaskDetailPanel from "../components/TaskDetailPanel";
import "./TaskPage.css";
import Header from '../components/Header';

function TaskPage({ nameInitials, currentProjectId }) {
  const { projectId } = useParams();
  
  const [tasks, setTasks] = useState([]);
  const [expanded, setExpanded] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState("");
  const [visibleDays, setVisibleDays] = useState(21);
  const [cellWidth, setCellWidth] = useState(40);
  const [userName, setUserName] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("전체");
  const [statusFilters, setStatusFilters] = useState({
    요청: true,
    진행: true,
    피드백: true,
    완료: true,
    보류: true,
  });
  const [filterOpen, setFilterOpen] = useState(false);
  
  // ✅ [신규] 고급 필터 상태
  const [advancedFilters, setAdvancedFilters] = useState({
    assignees: [],           // 선택된 담당자 목록
    dateRange: 'all',        // all/week/month/custom
    customStartDate: '',     // 커스텀 시작일
    customEndDate: '',       // 커스텀 종료일
    sortBy: '-created_date'  // 정렬 기준
  });

  // 상세 패널용 상태
  const [selectedTask, setSelectedTask] = useState(null);

  // 드래그 스크롤용
  const tableContainerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);

  // 하위업무 추가할 때 사용할 부모 ID
  const [subtaskParentId, setSubtaskParentId] = useState("");

  // 루트 업무만 뽑아서 옵션으로 보여줍니다
  const topLevelTasks = tasks.filter((t) => t.parent_task == null);

  const [currentUserId, setCurrentUserId] = useState(null);
  
  // ✅ [신규] 팀원 목록
  const [teamMembers, setTeamMembers] = useState([]);

  // 사용자 정보 (이름)
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await api.get("/api/users/name/");
        setUserName(response.data.name);
        setCurrentUserId(response.data.user_id);
      } catch (error) {
        console.error("사용자 정보 가져오기 실패:", error);
      }
    };
    fetchUserInfo();
  }, []);

  // ✅ [신규] 팀원 목록 가져오기
  useEffect(() => {
    if (projectId) {
      const fetchTeamMembers = async () => {
        try {
          const response = await api.get(`/api/team-members/?project_id=${projectId}`);
          setTeamMembers(response.data);
        } catch (error) {
          console.error("팀원 목록 가져오기 실패:", error);
        }
      };
      fetchTeamMembers();
    }
  }, [projectId]);

  // projectId 변화 시 업무 목록 로드
  useEffect(() => {
    if (projectId) {
      fetchTasksByProject(projectId);
    }
  }, [projectId]);

  // ✅ [신규] 필터 변경 시 자동 재조회
  useEffect(() => {
    if (projectId) {
      fetchTasksByProject(projectId);
    }
  }, [searchTerm, advancedFilters, statusFilters, categoryFilter]);

  // ✅ [개선] 업무 목록 API (필터 파라미터 포함)
  const fetchTasksByProject = async (id) => {
    try {
      // 쿼리 파라미터 구성
      const params = new URLSearchParams({
        project_id: id
      });
      
      // 검색어
      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim());
      }
      
      // 담당자 필터
      if (advancedFilters.assignees.length > 0) {
        params.append('assignees', advancedFilters.assignees.join(','));
      }
      
      // 상태 필터
      const activeStatuses = Object.entries(statusFilters)
        .filter(([_, enabled]) => enabled)
        .map(([status]) => {
          const statusMap = { '요청': '0', '진행': '1', '피드백': '2', '완료': '3', '보류': '4' };
          return statusMap[status] || status;
        });
      
      if (activeStatuses.length > 0 && activeStatuses.length < 5) {
        params.append('statuses', activeStatuses.join(','));
      }
      
      // 카테고리 필터 (내 업무)
      if (categoryFilter === "내 업무" && userName) {
        params.append('assignees', userName);
      }
      
      // 날짜 범위 필터
      if (advancedFilters.dateRange === 'week') {
        const today = new Date();
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - today.getDay());
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        
        params.append('start_after', weekStart.toISOString().split('T')[0]);
        params.append('end_before', weekEnd.toISOString().split('T')[0]);
      } else if (advancedFilters.dateRange === 'month') {
        const today = new Date();
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        params.append('start_after', monthStart.toISOString().split('T')[0]);
        params.append('end_before', monthEnd.toISOString().split('T')[0]);
      } else if (advancedFilters.dateRange === 'custom') {
        if (advancedFilters.customStartDate) {
          params.append('start_after', advancedFilters.customStartDate);
        }
        if (advancedFilters.customEndDate) {
          params.append('end_before', advancedFilters.customEndDate);
        }
      }
      
      // 정렬
      if (advancedFilters.sortBy) {
        params.append('ordering', advancedFilters.sortBy);
      }
      
      const response = await api.get(`/api/tasks/?${params.toString()}`);
      const data = response.data;

      const tasksArray = Array.isArray(data) ? data : (data.results || []);

      // 상태 숫자 → 라벨 변환
      const mapped = tasksArray.map((task) => ({
        ...task,
        task_name: task.task_name || "제목 없음",
        start_date: task.start_date || new Date().toISOString(),
        end_date: task.end_date || new Date().toISOString(),
        status:
          task.status == 0 ? "요청" :
          task.status == 1 ? "진행" :
          task.status == 2 ? "피드백" :
          task.status == 3 ? "완료" : "보류",
        assignee: task.assignee || "미정",
        parent_task_id: task.parent_task || null,
      }));
      
      setTasks(mapped);
    } catch (e) {
      console.error("업무 불러오기 실패", e);
    }
  };

  // onUpdate 콜백 - 여러 업무 동시 업데이트 지원
  const handleTaskUpdate = (updatedTask) => {
    setTasks((prevTasks) =>
      prevTasks.map((t) => {
        if (t.task_id === updatedTask.task_id) {
          return { ...t, ...updatedTask };
        }
        return t;
      })
    );
    
    setSelectedTask((prev) => {
      if (prev && prev.task_id === updatedTask.task_id) {
        return { ...prev, ...updatedTask };
      }
      return prev;
    });
  };

  // ✅ [변경] 백엔드에서 필터링하므로 그대로 사용
  const filteredTasks = tasks;

  // 트리 구조 생성 함수
  const buildTree = (tasks) => {
    const map = {};
    const roots = [];
    tasks.forEach((t) => (map[t.task_id] = { ...t, children: [] }));
    tasks.forEach((t) => {
      if (t.parent_task_id && map[t.parent_task_id]) {
        map[t.parent_task_id].children.push(map[t.task_id]);
      } else {
        roots.push(map[t.task_id]);
      }
    });
    return roots;
  };
  const filteredTree = buildTree(filteredTasks);

  // 트리 확장/접기 토글
  const toggleExpand = (taskId) => {
    const newSet = new Set(expanded);
    newSet.has(taskId) ? newSet.delete(taskId) : newSet.add(taskId);
    setExpanded(newSet);
  };

  // 날짜 계산 함수들
  const parseDate = (dateStr) => (dateStr ? new Date(dateStr) : null);
  const addDays = (date, days) => {
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() + days);
    return newDate;
  };
  const generateDateRange = (start, days) => {
    const arr = [];
    for (let i = 0; i < days; i++) {
      arr.push(addDays(start, i));
    }
    return arr;
  };

  // 날짜 범위 계산
  const startDates = tasks
    .map((t) => parseDate(t.start_date))
    .filter((d) => d && !isNaN(d.getTime()));
  const minStart =
    startDates.length > 0 ? new Date(Math.min(...startDates)) : new Date();
  
  const endDates = tasks
    .map((t) => parseDate(t.end_date))
    .filter((d) => d && !isNaN(d.getTime()));

  const maxEnd =
    endDates.length > 0
      ? new Date(Math.max(...endDates.map((d) => d.getTime())))
      : addDays(minStart, visibleDays - 1);
    
  const fullDays = Math.max(1, Math.floor((maxEnd - minStart)/(1000*60*60*24)) + 5);
  const fullDateRange = generateDateRange(minStart, fullDays);
  const dateRange = fullDateRange;

  // 헤더 그룹
  const groupDates = (dates) => ({
    mode: "day",
    groups: dates.map((d) => ({
      label: d.getDate(),
      ym: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
    })),
  });
  const headerGroups = groupDates(dateRange);

  // 바 스타일 계산
  const calcBarStyle = (start, end, status) => {
    const s = parseDate(start), e = parseDate(end);
    if (!s || !e) return { left: 0, width: 0 };
    const offsetDays = Math.floor((s - minStart) / (1000*60*60*24));
    let durDays = Math.floor((e - s) / (1000*60*60*24)) + 1;
    if (durDays < 1) durDays = 1;

    return {
      position: "absolute",
      top: '50%',
      transform: 'translateY(-50%)',
      left: `${offsetDays * cellWidth}px`,
      width: `${durDays * cellWidth}px`,
      height: "20px",
      borderRadius: "10px",
      backgroundColor: getStatusColor(status)
    };
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "요청": return "#2196F3";
      case "진행": return "#13a75d";
      case "피드백": return "#FF9800";
      case "완료": return "rgb(163, 156, 231)";
      default: return "#909399";
    }
  };

  const handleTaskNameClick = (task) => {
    if (selectedTask && selectedTask.task_id === task.task_id) {
      setSelectedTask(null);
    } else {
      setSelectedTask(task);
    }
  };

  // 드래그 핸들러
  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
    const rect = tableContainerRef.current.getBoundingClientRect();
    setStartX(e.clientX - rect.left);
    setScrollLeft(tableContainerRef.current.scrollLeft);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const rect = tableContainerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const walk = x - startX;
    tableContainerRef.current.scrollLeft = scrollLeft - walk;
  };

  const handleMouseUp = () => setIsDragging(false);
  const handleMouseLeave = () => setIsDragging(false);

  // 업무 추가 핸들러
  const handleAddTask = async () => {
    const name = window.prompt("상위 업무명을 입력하세요");
    if (!name?.trim()) return;
    if (!currentUserId) {
      alert("사용자 정보가 아직 로드되지 않았습니다.");
      return;
    }
    try {
      await api.post(
        "/api/tasks/",
        {
          task_name: name,
          status: 0,
          start_date: new Date().toISOString().split('T')[0],
          end_date: new Date().toISOString().split('T')[0],
          parent_task: null,
          project_id: projectId,
          user: currentUserId
        }
      );
      fetchTasksByProject(projectId);
    } catch (err) {
      console.error("업무 추가 실패:", err);
      alert("업무 추가에 실패했습니다.");
    }
  };

  const handleAddSubtask = async (parentId) => {
    const name = window.prompt("하위 업무명을 입력하세요");
    if (!name?.trim()) return;
    if (!currentUserId) return;

    try {
      await api.post(
        "/api/tasks/",
        {
          task_name: name,
          status: 0,
          start_date: new Date().toISOString().split('T')[0],
          end_date: new Date().toISOString().split('T')[0],
          parent_task: parentId,
          project_id: projectId,
          user: currentUserId
        }
      );
      setExpanded(s => new Set(s).add(parentId));
      fetchTasksByProject(projectId);
    } catch (err) {
      console.error("하위 업무 추가 실패:", err);
      alert("하위 업무 추가에 실패했습니다.");
    }
  };

  // Flatten 트리
  const flatList = [];
  const flatten = (nodes, level = 0) => {
    nodes.forEach(n => {
      flatList.push({ task: n, level });
      if (expanded.has(n.task_id) && n.children) {
        flatten(n.children, level + 1);
      }
    });
  };
  flatten(filteredTree);

  // 주차 그룹 생성
  const buildWeekGroups = (dates) => {
    const weeks = [];
    for (let i = 0; i < dates.length; i += 7) {
      const weekIndex = Math.floor(i / 7) + 1;
      const span = Math.min(7, dates.length - i);
      weeks.push({ label: `${weekIndex}주차`, span });
    }
    return weeks;
  };
  const weekGroups = buildWeekGroups(fullDateRange);

  return (
    <div className="TaskPage_wrapper">
      <div className="TaskPage_Topbarst_header">
        <Header nameInitials={nameInitials} currentProjectId={currentProjectId} />
        <Topbarst />
        <Topbar />
        
        {/* 컨트롤 바 */}
        <div className="TaskPage_controlRow">
          <div className="ControlLeft">
            <input
              type="text"
              className="TaskNameInput"
              placeholder="업무명 또는 설명을 검색하세요"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="ControlRight">
            <button className="TaskPage_FilterButton" onClick={() => setFilterOpen(!filterOpen)}>
              필터 {filterOpen ? '▲' : '▼'}
            </button>
            <div className="ZoomAndNew">
              <button onClick={() => setCellWidth(w => Math.max(20, w - 5))}>–</button>
              <button onClick={() => setCellWidth(w => Math.min(100, w + 5))}>+</button>
              <button className="AddTaskButton" onClick={handleAddTask}>
                <FaPlus /> 상위 업무 추가
              </button>
              <select
                className="ParentSelect"
                value={subtaskParentId}
                onChange={e => {
                  const pid = e.target.value;
                  setSubtaskParentId(pid);
                  if (pid) {
                    handleAddSubtask(pid);
                    setSubtaskParentId("");
                  }
                }}
              >
                <option value="">하위 업무 추가</option>
                {topLevelTasks.map(t => (
                  <option key={t.task_id} value={t.task_id}>{t.task_name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ✅ [개선] 필터 패널 - 가로/세로 혼합 레이아웃 */}
      {filterOpen && (
        <div className="FilterPanel">
          {/* 카테고리 (세로) */}
          <div className="FilterSection FilterSection_vertical">
            <h4>카테고리</h4>
            <label>
              <input 
                type="radio" 
                name="category" 
                value="전체" 
                checked={categoryFilter==="전체"} 
                onChange={e=>setCategoryFilter(e.target.value)}
              />
              전체
            </label>
            <label>
              <input 
                type="radio" 
                name="category" 
                value="내 업무" 
                checked={categoryFilter==="내 업무"} 
                onChange={e=>setCategoryFilter(e.target.value)}
              />
              내 업무
            </label>
          </div>

          {/* 나머지 필터들 (가로) */}
          <div className="FilterSection FilterSection_horizontal">
            {/* 담당자 */}
            <div className="FilterGroup">
              <h4>담당자</h4>
              <div className="FilterScrollBox">
                {teamMembers.length > 0 ? (
                  teamMembers.map(member => (
                    <label key={member.user_id}>
                      <input
                        type="checkbox"
                        checked={advancedFilters.assignees.includes(member.name)}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setAdvancedFilters(prev => ({
                            ...prev,
                            assignees: checked 
                              ? [...prev.assignees, member.name]
                              : prev.assignees.filter(a => a !== member.name)
                          }));
                        }}
                      />
                      {member.name}
                    </label>
                  ))
                ) : (
                  <p className="NoData">팀원 없음</p>
                )}
              </div>
            </div>

            {/* 날짜 범위 */}
            <div className="FilterGroup">
              <h4>날짜 범위</h4>
              <label>
                <input 
                  type="radio" 
                  name="dateRange" 
                  value="all"
                  checked={advancedFilters.dateRange === 'all'}
                  onChange={() => setAdvancedFilters(prev => ({ ...prev, dateRange: 'all' }))}
                />
                전체
              </label>
              <label>
                <input 
                  type="radio" 
                  name="dateRange" 
                  value="week"
                  checked={advancedFilters.dateRange === 'week'}
                  onChange={() => setAdvancedFilters(prev => ({ ...prev, dateRange: 'week' }))}
                />
                이번 주
              </label>
              <label>
                <input 
                  type="radio" 
                  name="dateRange" 
                  value="month"
                  checked={advancedFilters.dateRange === 'month'}
                  onChange={() => setAdvancedFilters(prev => ({ ...prev, dateRange: 'month' }))}
                />
                이번 달
              </label>
              <label>
                <input 
                  type="radio" 
                  name="dateRange" 
                  value="custom"
                  checked={advancedFilters.dateRange === 'custom'}
                  onChange={() => setAdvancedFilters(prev => ({ ...prev, dateRange: 'custom' }))}
                />
                커스텀
              </label>
              
              {advancedFilters.dateRange === 'custom' && (
                <div className="DateInputs">
                  <input
                    type="date"
                    value={advancedFilters.customStartDate}
                    onChange={(e) => setAdvancedFilters(prev => ({ 
                      ...prev, 
                      customStartDate: e.target.value 
                    }))}
                  />
                  <span>~</span>
                  <input
                    type="date"
                    value={advancedFilters.customEndDate}
                    onChange={(e) => setAdvancedFilters(prev => ({ 
                      ...prev, 
                      customEndDate: e.target.value 
                    }))}
                  />
                </div>
              )}
            </div>

            {/* 정렬 */}
            <div className="FilterGroup">
              <h4>정렬</h4>
              <select
                value={advancedFilters.sortBy}
                onChange={(e) => setAdvancedFilters(prev => ({ 
                  ...prev, 
                  sortBy: e.target.value 
                }))}
              >
                <option value="-created_date">생성일 (최신순)</option>
                <option value="created_date">생성일 (오래된순)</option>
                <option value="end_date">마감일 (빠른순)</option>
                <option value="-end_date">마감일 (느린순)</option>
                <option value="status">상태 (요청→완료)</option>
                <option value="-status">상태 (완료→요청)</option>
                <option value="task_name">업무명 (가나다순)</option>
                <option value="-task_name">업무명 (역순)</option>
              </select>
            </div>

            {/* 상태 */}
            <div className="FilterGroup">
              <h4>상태</h4>
              {Object.keys(statusFilters).map(status => (
                <label key={status}>
                  <input
                    type="checkbox"
                    checked={statusFilters[status]}
                    onChange={(e) => setStatusFilters(prev => ({
                      ...prev,
                      [status]: e.target.checked
                    }))}
                  />
                  {status}
                </label>
              ))}
            </div>
          </div>

          {/* 필터 초기화 */}
          <button
            className="ResetFilterButton"
            onClick={() => {
              setSearchTerm("");
              setCategoryFilter("전체");
              setStatusFilters({
                요청: true,
                진행: true,
                피드백: true,
                완료: true,
                보류: true,
              });
              setAdvancedFilters({
                assignees: [],
                dateRange: 'all',
                customStartDate: '',
                customEndDate: '',
                sortBy: '-created_date'
              });
            }}
          >
            필터 초기화
          </button>
        </div>
      )}

      {/* 간트차트 테이블 컨테이너 */}
      <div className="GanttContainer">
        {/* 왼쪽 고정 컬럼 */}
        <table className="LeftTable">
          <thead>
            <tr>
              <th className="col-task">업무명</th>
              <th className="col-assignee">담당자</th>
              <th className="col-status">상태</th>
            </tr>
          </thead>
          <tbody>
            {flatList.map(({ task, level }) => (
              <tr key={task.task_id}>
                <td className="col-task">
                  <div
                    className="TreeItem"
                    style={{ paddingLeft: level * 20 + "px", cursor: "pointer" }}
                    onClick={() => handleTaskNameClick(task)}
                  >
                    {task.children && task.children.length > 0 && (
                      <span
                        className="ToggleBtn"
                        onClick={e => {
                          e.stopPropagation();
                          toggleExpand(task.task_id);
                        }}
                      >
                        {expanded.has(task.task_id) ? <FaCaretDown /> : <FaCaretRight />}
                      </span>
                    )}
                    <span>{task.task_name}</span>
                  </div>
                </td>
                <td className="col-assignee">{task.assignee}</td>
                <td className="col-status">
                  <span className={`StatusBadge status-${task.status}`}>{task.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* 오른쪽 간트 차트 */}
        <div
          className={`RightTableWrapper ${isDragging ? "dragging" : ""}`}
          ref={tableContainerRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        >
          <table className="RightTable">
            <thead>
              {cellWidth === 20 ? (
                <tr className="week_tr">
                  {weekGroups.map(({ label, span }, i) => (
                    <th key={i} style={{ width: `${span * cellWidth}px`, minWidth: `${span * cellWidth}px` }}>
                      {label}
                    </th>
                  ))}
                </tr>
              ) : (
                <tr>
                  {fullDateRange.map((d, i) => (
                    <th key={i} style={{ width: `${cellWidth}px`, minWidth: `${cellWidth}px` }}>
                      {d.getDate()}
                    </th>
                  ))}
                </tr>
              )}
            </thead>
            <tbody>
              {flatList.map(({ task }) => (
                <tr key={task.task_id}>
                  {/* ✅ [수정] 각 날짜별로 td 분할하여 세로 그리드 라인 표시 */}
                  {fullDateRange.map((_, dayIndex) => (
                    <td key={dayIndex} className="gantt-cell-day">
                      {dayIndex === 0 && (
                        <div className="gantt-bar" style={calcBarStyle(task.start_date, task.end_date, task.status)} />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 상세 패널 */}
      {selectedTask && (
        <div className="TaskPage_rightSide">
          <TaskDetailPanel
            task={selectedTask}
            projectId={projectId}
            onClose={() => setSelectedTask(null)}
            onUpdate={handleTaskUpdate}
          />
        </div>
      )}
    </div>
  );
}

export default TaskPage;
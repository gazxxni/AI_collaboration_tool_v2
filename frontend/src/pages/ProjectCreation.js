import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FaArrowUp, FaCalendarAlt } from 'react-icons/fa'; // 사용하지 않는 아이콘 정리
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import './ProjectCreation.css';
import Invite from './Invite';

// [수정] Toast는 함수만 가져옵니다 (Container는 App.js에 있음)
import { toast } from 'react-toastify';

function ProjectCreation() {
  const [userName, setUserName] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [projectGoal, setProjectGoal] = useState('');
  const [techStack, setTechStack] = useState([]);
  const [tasks, setTasks] = useState([]); // tasks 상태 유지 (필요 시)

  const [teamMembers, setTeamMembers] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [loading, setLoading] = useState(false);
  const formRef = useRef(null);

  // [추가] 컴포넌트가 마운트 상태인지 확인하는 Ref (페이지 이동 후 state 업데이트 방지용)
  const isMounted = useRef(true);

  const navigate = useNavigate();

  // 컴포넌트 마운트/언마운트 추적
  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    const fetchUserName = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/users/name/', { withCredentials: true });
        if (isMounted.current) setUserName(response.data.name);
      } catch (error) {
        console.error('사용자 이름을 가져오는 데 실패했습니다.');
      }
    };
    fetchUserName();
  }, []);

  const handleTeamMembersUpdate = () => {
    try {
      const storedTeamMembers = sessionStorage.getItem('team_member');
      if (storedTeamMembers) {
        if (isMounted.current) setTeamMembers(JSON.parse(storedTeamMembers));
      }
    } catch (error) {
      console.error('팀원 정보 업데이트 중 오류:', error);
    }
  };

  useEffect(() => {
    const storedTeamMembers = sessionStorage.getItem('team_member');
    if (storedTeamMembers) {
      setTeamMembers(JSON.parse(storedTeamMembers));
    }

    window.addEventListener('teamMembersUpdated', handleTeamMembersUpdate);
    return () => {
      window.removeEventListener('teamMembersUpdated', handleTeamMembersUpdate);
    };
  }, []);

  useEffect(() => {
    if (!isModalOpen) {
      handleTeamMembersUpdate();
    }
  }, [isModalOpen]);

  // ▼ 핵심 수정 부분 ▼
  const handleCreateTasks = async (e) => {
    e.preventDefault();
    if (!projectName) return toast.warning('프로젝트 이름을 입력해주세요.');
    if (!startDate || !endDate) return toast.warning('시작일과 마감일을 선택해주세요.');

    sessionStorage.setItem('project_name', projectName);

    const storedTeamMembers = sessionStorage.getItem('team_member');
    const teamData = storedTeamMembers ? JSON.parse(storedTeamMembers) : [];
    const selectedUserIds = teamData.map((member) => member.user_id);

    if (selectedUserIds.length === 0) return toast.warning('최소 한 명 이상 초대해야 합니다.');

    // 1. "생성 중" 알림 띄우기 (autoClose: false로 설정하여 계속 유지됨)
    const toastId = toast.loading("AI가 업무를 생성하고 있습니다. 다른 작업을 하셔도 됩니다.", {
      position: "bottom-right",
    });
    
    setLoading(true);

    try {
      const startStr = startDate.toISOString().split('T')[0];
      const endStr = endDate.toISOString().split('T')[0];

      // 비동기 요청 (페이지를 떠나도 브라우저 백그라운드에서 계속 실행됨)
      const response = await axios.post('http://127.0.0.1:8000/gptapi/generate-tasks/', {
        project_topic: projectName,
        project_description: projectDescription,
        project_goal: projectGoal,
        tech_stack: techStack,
        selected_users: selectedUserIds,
        project_start_date: startStr,
        project_end_date: endStr
      });

      // 2. 성공 시 처리 로직
      // 컴포넌트가 언마운트 되었더라도 toast.update는 전역(App.js)에서 동작하므로 실행됨
      
      toast.update(toastId, {
        render: "🎉 업무 생성이 완료되었습니다! 여기를 클릭하여 확인하세요.",
        type: "success",
        isLoading: false,
        autoClose: false, // 사용자가 클릭할 때까지 사라지지 않음 (혹은 5000ms 등 설정 가능)
        closeOnClick: true, // 클릭하면 닫히면서 onClick 이벤트 실행
        draggable: true,
        // [핵심] 알림 클릭 시 이동 로직
        onClick: () => {
          navigate('/project-detail', {
            state: {
              projectName: response.data.project_name || projectName,
              projectId: null,
              tasks: response.data.tasks,
              selectedUsers: selectedUserIds,
              start_date: startStr,
              end_date: endStr,
              project_description: projectDescription,
              project_goal: projectGoal,
              tech_stack: techStack
            }
          });
        }
      });

      // 현재 페이지에 남아있다면 로딩 상태 해제
      if (isMounted.current) {
        setLoading(false);
        setTasks(response.data.tasks);
      }

    } catch (error) {
      if (isMounted.current) setLoading(false);

      // 에러 처리
      if (error.response?.status === 400 && error.response.data?.invalid_fields) {
        const fields = error.response.data.invalid_fields;
        const fieldLabels = {
          "프로젝트 이름": "프로젝트 이름",
          "설명": "프로젝트 설명",
          "목표": "프로젝트 목표 및 산출물"
        };
        const fieldNames = fields.map(f => fieldLabels[f] || f);
        
        toast.update(toastId, {
          render: `입력 정보 부족: ${fieldNames.join(', ')}`,
          type: "error",
          isLoading: false,
          autoClose: false
        });
      } else {
        toast.update(toastId, {
          render: "업무 생성 실패. 다시 시도해주세요.",
          type: "error",
          isLoading: false,
          autoClose: false
        });
      }
    }
  };

  useEffect(() => {
    setIsModalOpen(true);
  }, []);

  const handleModalClose = () => {
    setIsModalOpen(false);
    setTimeout(() => handleTeamMembersUpdate(), 100);
  };

  const availableTech = [
    'React', 'Vue.js', 'Django', 'FastAPI', 'Node.js', 
    'Spring Boot', 'Firebase', 'MySQL', 'MongoDB', 
    'Figma', 'AWS', 'Docker',
  ];

  return (
    <div>
      {/* ToastContainer는 App.js로 이동했으므로 여기서 삭제 */}

      <div className="ProjectContainer">
        <h1 className="ProjectTitle">새 프로젝트</h1>

        <div className="DateAndTeamRow">
          <div className="DatePickers">
            <div className="DatePickerContainer">
              <DatePicker
                selected={startDate}
                onChange={(date) => setStartDate(date)}
                placeholderText="시작 날짜"
                className="DateInput"
                minDate={new Date()}
              />
              <FaCalendarAlt className="CalendarIcon" />
            </div>
            <div className="DatePickerContainer">
              <DatePicker
                selected={endDate}
                onChange={(date) => setEndDate(date)}
                placeholderText="마감 날짜"
                className="DateInput"
                minDate={startDate || new Date()}
              />
              <FaCalendarAlt className="CalendarIcon" />
            </div>
          </div>

          <div className="TeamProfiles">
            {teamMembers.map((member) => (
              <div key={member.user_id} className="ProfileCircle">
                {member.name}
              </div>
            ))}
          </div>
        </div>

        <form ref={formRef} className="ProjectForm" onSubmit={handleCreateTasks}>
          <label className="ProjectLabel">프로젝트 이름</label>
          <div className="ProjectInputWrapper">
            <input
              type="text"
              className="ProjectInput"
              placeholder="예: 학내 커뮤니티 기반 중고마켓 앱 개발"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
            />
          </div>
        </form>

        <div className="ProjectFormGroup">
          <label className="ProjectLabel">프로젝트 설명</label>
          <textarea
            className="ProjectTextArea"
            placeholder="예: 학내 구성원 간 커뮤니티 기반으로 중고 물품을 거래할 수 있는 온라인 플랫폼을 개발합니다..."
            value={projectDescription}
            onChange={(e) => setProjectDescription(e.target.value)}
          />

          <label className="ProjectLabel">프로젝트 목표 및 산출물</label>
          <textarea
            className="ProjectTextArea"
            placeholder="예: 주요 목표는 모바일과 웹 환경에서 모두 사용할 수 있는 반응형 중고마켓 앱을 완성하는 것입니다..."
            value={projectGoal}
            onChange={(e) => setProjectGoal(e.target.value)}
          />

          <label className="ProjectLabel">사용 기술 스택 (선택 사항)</label>
          <div className="TechStackContainer">
            {availableTech.map((tech) => (
              <label key={tech} className="TechCheckbox">
                <input
                  type="checkbox"
                  value={tech}
                  checked={techStack.includes(tech)}
                  onChange={(e) =>
                    setTechStack((prev) =>
                      e.target.checked ? [...prev, tech] : prev.filter((t) => t !== tech)
                    )
                  }
                />
                {tech}
              </label>
            ))}
          </div>
          
          <div className='ProjectCreation_footer'>
            <button
              type="button"
              className='ProjectCreation_footer_btn'
              disabled={loading}
              onClick={() => formRef.current?.requestSubmit()}
              style={{ cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
            >
              {loading ? '생성 중...' : '생성하기'}
            </button>   
          </div>
        </div>
      </div>

      {isModalOpen && <Invite onClose={handleModalClose} />}
    </div>
  );
}

export default ProjectCreation;
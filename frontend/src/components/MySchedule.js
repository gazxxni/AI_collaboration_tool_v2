/* eslint-disable */
// src/components/MySchedule.js
import React, { useState, useEffect } from "react";
import Calendar from "react-calendar";
import "react-calendar/dist/Calendar.css";
import ScheduleModal from "./ScheduleModal"; 
import "./MySchedule.css";
import api from "../api/axios"; // ✅ API 모듈 import

function MySchedule({ onClose }) {
  const [events, setEvents] = useState({});
  const [date, setDate] = useState(new Date());
  const [activeStartDate, setActiveStartDate] = useState(new Date()); 
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTitle, setSelectedTitle] = useState("");

  // 일정 목록을 불러오는 함수
  const fetchSchedules = async () => {
    try {
      // ✅ api 모듈 사용 & 올바른 경로(/api/schedule/list/)로 수정
      const response = await api.get("/api/schedule/list/");
      console.log("📌 불러온 일정 데이터:", response.data);

      const formattedEvents = {};
      response.data.forEach((schedule) => {
        const formattedDate = new Date(schedule.start_time)
          .toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" })
          .replace(/\. /g, "-")
          .replace(/\./g, "");
        formattedEvents[formattedDate] = { id: schedule.schedule_id, title: schedule.title };
      });

      setEvents(formattedEvents);
    } catch (error) {
      console.error("📌 일정 불러오기 실패:", error);
    }
  };

  useEffect(() => {
    fetchSchedules();
  }, []);

  // 날짜 클릭 시 모달 열기
  const handleDateClick = (value) => {
    if (value.getMonth() !== activeStartDate.getMonth()) return;
    const formattedDate = value
      .toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" })
      .replace(/\. /g, "-")
      .replace(/\./g, "");
    setSelectedDate(formattedDate);
    setSelectedTitle(events[formattedDate]?.title || "");
  };

  // 일정 저장 (추가 또는 수정)
  const handleSaveSchedule = async () => {
    if (!selectedDate || !selectedTitle.trim()) {
      alert("일정 제목을 입력해주세요.");
      return;
    }
  
    try {
      if (events[selectedDate]) {
        // 기존 일정이 있을 경우 수정 (PUT)
        // ✅ api 모듈 사용 & 경로 수정
        await api.put(
          `/api/schedule/update/${events[selectedDate].id}/`,
          { title: selectedTitle, start_time: selectedDate, end_time: selectedDate }
        );
        console.log(`✅ ${selectedDate} 일정 업데이트됨.`);
      } else {
        // 새 일정 추가 (POST)
        // ✅ api 모듈 사용 & 경로 수정
        await api.post(
          "/api/schedule/create/",
          { title: selectedTitle, start_time: selectedDate, end_time: selectedDate }
        );
        console.log(`✅ ${selectedDate}에 일정 추가됨.`);
      }
      fetchSchedules();
      setSelectedDate(null); 
    } catch (error) {
      console.error(`📌 ${selectedDate} 일정 저장 실패:`, error);
    }
  };
  
  // 일정 삭제
  const handleDeleteSchedule = async () => {
    if (!selectedDate || !events[selectedDate]) return;

    try {
      // ✅ api 모듈 사용 & 경로 수정
      await api.delete(`/api/schedule/delete/${events[selectedDate].id}/`);
      console.log(`🗑️ ${selectedDate} 일정 삭제됨.`);
      fetchSchedules();
      setSelectedDate(null); 
    } catch (error) {
      console.error(`📌 ${selectedDate} 일정 삭제 실패:`, error);
    }
  };

  return (
    <section className="MySchedule_container custom-schedule">
      <div style={{ height: "5vh" }}></div>

      {/* 캘린더 */}
      <Calendar
        onChange={setDate}
        value={date}
        onClickDay={handleDateClick}
        locale="ko-KR"
        calendarType="gregory"
        onActiveStartDateChange={({ activeStartDate }) => setActiveStartDate(activeStartDate)}
        tileClassName={({ date }) => {
          if (date.getMonth() !== activeStartDate.getMonth()) {
            return "neighboring-month";
          }
          const day = date.getDay();
          if (day === 0) return "sunday";
          if (day === 6) return "saturday";
          return "";
        }}
        tileContent={({ date }) => {
          const formattedDate = date
            .toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" })
            .replace(/\. /g, "-")
            .replace(/\./g, "");
          
          if (events[formattedDate]) {
            const isCurrentMonth = date.getMonth() === activeStartDate.getMonth();
            return (
              <div className="event-marker">
                <span className={isCurrentMonth ? "" : "gray-text"} style={{ display: "block", fontWeight: "bold" }}>
                  {events[formattedDate].title}
                </span>
              </div>
            );
          }
          return null;
        }}
      />

      {/* ScheduleModal을 사용하여 모달 창으로 일정 추가/수정 UI 렌더링 */}
      <ScheduleModal
        isOpen={selectedDate !== null}
        onRequestClose={() => setSelectedDate(null)}
        contentLabel="일정 수정/추가"
        style={{
          content: {
            width: "30vw",
            height: "30vh",
            top: "0%",
            left: "0%",
          }
        }}
      >
        <button
            className="Invite_close_btn"
            onClick={() => setSelectedDate(null)}
            >
            ✖
        </button>
        <div className="MySchedule-Text">
            <h3>{selectedDate} 일정</h3>
        </div>
        <div className="MySchedule-Item">
          <div className="MySchedule-container">
            <input className="MySchedule-input"
                  type="text"
                  placeholder="일정 제목 입력"
                  value={selectedTitle}
                  onChange={(e) => setSelectedTitle(e.target.value)}
                  maxLength={21}
              />
          </div>
            <div className="MySchedule-buttons">
              <button onClick={handleSaveSchedule} className="MySchedule-save-button" >저장✅</button>
              {events[selectedDate] && <button onClick={handleDeleteSchedule} className="MySchedule-delete-button" >삭제❌</button>}
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{
                fontSize: "12px",
                fontWeight: "bold",
                display: "inline-block",
                marginTop:"3vh"
              }}>
                🚨 최대 21자까지 작성 가능합니다.
              </span>
            </div>  
        </div>
      </ScheduleModal>
    </section>
  );
}

export default MySchedule;
from fastapi import APIRouter, HTTPException, Depends
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher
from schemas import QRAttendance

router = APIRouter(prefix="/classes", tags=["Classes"])

@router.get("/upcoming")
def get_upcoming_classes(user: dict = Depends(get_current_user)):
    """Get upcoming classes for student or teacher"""
    conn = get_connection()
    cur = conn.cursor()
    
    if user["role"] == "student":
        # Get student's group first
        cur.execute("SELECT group_id FROM students WHERE student_id = %s", (user["student_id"],))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Student group not found")
        group_id = row[0]
        
        # Get upcoming classes for this group
        cur.execute("""
            SELECT c.class_id, c.date, c.time, c.cabinet, 
                   t.teacher_name, g.group_name, c.subject
            FROM classes c
            JOIN teachers t ON t.teacher_id = c.teacher_id
            JOIN groups g ON g.group_id = c.group_id
            WHERE c.group_id = %s AND c.date >= CURRENT_DATE
            ORDER BY c.date, c.time
            LIMIT 10
        """, (group_id,))
    else:
        # Teacher sees their own schedule
        cur.execute("""
            SELECT c.class_id, c.date, c.time, c.cabinet, 
                   t.teacher_name, g.group_name, c.subject
            FROM classes c
            JOIN teachers t ON t.teacher_id = c.teacher_id
            JOIN groups g ON g.group_id = c.group_id
            WHERE c.teacher_id = (SELECT teacher_id FROM teachers WHERE email = %s)
            AND c.date >= CURRENT_DATE
            ORDER BY c.date, c.time
            LIMIT 10
        """, (user.get("email", ""),))
    
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    return {
        "upcoming_classes": [{
            "class_id": r[0],
            "date": str(r[1]),
            "time": str(r[2]),
            "cabinet": r[3],
            "teacher": r[4],
            "group": r[5],
            "subject": r[6]
        } for r in rows]
    }

@router.get("/schedule")
def get_full_schedule(user: dict = Depends(get_current_user)):
    """Get full schedule for teacher"""
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT c.class_id, c.date, c.time, c.cabinet, 
               t.teacher_name, g.group_name, c.subject
        FROM classes c
        JOIN teachers t ON t.teacher_id = c.teacher_id
        JOIN groups g ON g.group_id = c.group_id
        WHERE c.teacher_id = (SELECT teacher_id FROM teachers WHERE email = %s)
        ORDER BY c.date, c.time
    """, (user.get("email", ""),))
    
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    return {
        "schedule": [{
            "class_id": r[0],
            "date": str(r[1]),
            "time": str(r[2]),
            "cabinet": r[3],
            "teacher": r[4],
            "group": r[5],
            "subject": r[6]
        } for r in rows]
    }

@router.post("/attendance/qr")
def mark_attendance_qr(attendance: QRAttendance, user: dict = Depends(get_current_user)):
    """Mark attendance via QR code (for students)"""
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    
    if user["student_id"] != attendance.student_id:
        raise HTTPException(status_code=403, detail="Can only mark your own attendance")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Verify QR code and class
    cur.execute("""
        SELECT c.class_id, c.group_id 
        FROM classes c
        WHERE c.class_id = %s AND c.qr_code = %s
    """, (attendance.class_id, attendance.qr_code))
    
    class_row = cur.fetchone()
    if not class_row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Invalid class or QR code")
    
    class_id, group_id = class_row
    
    # Verify student is in this group
    cur.execute("SELECT group_id FROM students WHERE student_id = %s", (user["student_id"],))
    student_group = cur.fetchone()
    if not student_group or student_group[0] != group_id:
        cur.close(); conn.close()
        raise HTTPException(status_code=403, detail="You are not in this group")
    
    # Mark attendance
    cur.execute("""
        INSERT INTO attendance (student_id, class_id, status, marked_at)
        VALUES (%s, %s, 'PRESENT', CURRENT_TIMESTAMP)
        ON CONFLICT (student_id, class_id) DO UPDATE SET status = 'PRESENT', marked_at = CURRENT_TIMESTAMP
        RETURNING attendance_id
    """, (user["student_id"], class_id))
    
    attendance_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    
    return {"success": True, "attendance_id": attendance_id, "message": "Attendance marked successfully"}

@router.get("/{class_id}/students")
def get_class_students(class_id: int, user: dict = Depends(get_current_user)):
    """Get all students in a class (for teacher)"""
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get group_id for this class
    cur.execute("SELECT group_id FROM classes WHERE class_id = %s", (class_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Class not found")
    
    group_id = row[0]
    
    # Get all students in this group with their attendance status
    cur.execute("""
        SELECT s.student_id, s.student_name, s.email,
               COALESCE(a.status, 'ABSENT') as attendance_status
        FROM students s
        LEFT JOIN attendance a ON a.student_id = s.student_id AND a.class_id = %s
        WHERE s.group_id = %s
        ORDER BY s.student_name
    """, (class_id, group_id))
    
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    return {
        "class_id": class_id,
        "students": [{
            "student_id": r[0],
            "name": r[1],
            "email": r[2],
            "attendance_status": r[3]
        } for r in rows]
    }

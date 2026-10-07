from enum import Enum


class GenderEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"


class TestTypeEnum(str, Enum):
    PUSHUP = "PUSHUP"
    PULLUP = "PULLUP"
    COOPER = "COOPER"
    FLEXIBILITY = "FLEXIBILITY"


class WorkoutStatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    DISCARDED = "DISCARDED"
    SKIPPED = "SKIPPED"
    SCHEDULED = "SCHEDULED"


class SatisfactionEnum(str, Enum):
    LIKED = "Liked"
    DISLIKED = "Disliked"


class SlotTypeEnum(str, Enum):
    WARMUP = "warmup"
    MAIN = "main"
    COOLDOWN = "cooldown"


class DayOfWeekEnum(str, Enum):
    MONDAY = "MONDAY"
    WEDNESDAY = "WEDNESDAY"
    FRIDAY = "FRIDAY"


class PerceivedDifficultyEnum(str, Enum):
    VERY_EASY = "Very Easy"
    EASY = "Easy"
    NORMAL = "Normal"
    HARD = "Hard"
    VERY_HARD = "Very Hard"


class FatigueStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    NOT_ACTIVE = "NOT ACTIVE"


class UserRoleEnum(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class AttendanceStatusEnum(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class CreditStatusEnum(str, Enum):
    PASSED = "PASSED"
    NOT_PASSED = "NOT_PASSED"
    IN_PROGRESS = "IN_PROGRESS"


def enum_values(enum_class: type[Enum]) -> list[str]:
    return [item.value for item in enum_class]

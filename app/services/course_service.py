"""
app/services/course_service.py

Course business logic — notably versioning: editing a published course
never mutates it in place. Instead a new Course row is created with an
incremented version, the old row is flagged is_latest_version=False, and
lessons are copied across so the new version can be edited independently.
Existing Enrollments keep pointing at the version they enrolled in.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.learning import Course, Lesson, LearningPath
from app.models.base import CourseStatus
from app.schemas.learning import CourseCreate, CourseUpdate, LessonCreate


def get_learning_paths(db: Session, published_only: bool = True) -> List[LearningPath]:
    query = db.query(LearningPath)
    if published_only:
        query = query.filter(LearningPath.is_published.is_(True))
    return query.order_by(LearningPath.order_index).all()


def get_course_by_slug(db: Session, slug: str) -> Optional[Course]:
    """Returns the latest version of a course by slug."""
    return (
        db.query(Course)
        .options(joinedload(Course.lessons))
        .filter(Course.slug == slug, Course.is_latest_version.is_(True))
        .first()
    )


def get_course_by_id(db: Session, course_id: UUID) -> Course:
    course = (
        db.query(Course)
        .options(joinedload(Course.lessons))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


def list_published_courses(db: Session, learning_path_id: Optional[UUID] = None) -> List[Course]:
    query = db.query(Course).filter(
        Course.status == CourseStatus.PUBLISHED,
        Course.is_latest_version.is_(True),
    )
    if learning_path_id:
        query = query.filter(Course.learning_path_id == learning_path_id)
    return query.order_by(Course.order_index).all()


def create_course(db: Session, course_in: CourseCreate, created_by_ai: bool = False) -> Course:
    existing = (
        db.query(Course)
        .filter(Course.slug == course_in.slug, Course.is_latest_version.is_(True))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A course with this slug already exists. Use the update endpoint to create a new version.",
        )

    course = Course(**course_in.model_dump(), generated_by_ai=created_by_ai, version=1, is_latest_version=True)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def add_lesson(db: Session, course_id: UUID, lesson_in: LessonCreate) -> Lesson:
    course = get_course_by_id(db, course_id)
    if course.status == CourseStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot add lessons to a published course directly — create a new version first.",
        )
    lesson = Lesson(course_id=course.id, **lesson_in.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def publish_course(db: Session, course_id: UUID) -> Course:
    course = get_course_by_id(db, course_id)
    if not course.lessons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a course with no lessons.",
        )
    course.status = CourseStatus.PUBLISHED
    db.commit()
    db.refresh(course)
    return course


def update_course_metadata(db: Session, course_id: UUID, updates: CourseUpdate) -> Course:
    """
    For DRAFT courses only — direct edits are fine pre-publish.
    Published courses must go through create_new_version() instead.
    """
    course = get_course_by_id(db, course_id)
    if course.status == CourseStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit a published course directly. Create a new version instead.",
        )
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


def create_new_version(db: Session, course_id: UUID) -> Course:
    """
    Creates version N+1 of a published course, copying all lessons across.
    The old version stays untouched (and is_latest_version flips to False)
    so students already enrolled finish the version they started.
    """
    old_course = get_course_by_id(db, course_id)

    new_course = Course(
        learning_path_id=old_course.learning_path_id,
        title=old_course.title,
        slug=old_course.slug,
        description=old_course.description,
        thumbnail_url=old_course.thumbnail_url,
        version=old_course.version + 1,
        is_latest_version=True,
        previous_version_id=old_course.id,
        status=CourseStatus.DRAFT,
        order_index=old_course.order_index,
        pass_mark_percent=old_course.pass_mark_percent,
        certificate_fee_kobo=old_course.certificate_fee_kobo,
        requires_capstone=old_course.requires_capstone,
        generated_by_ai=False,
    )
    db.add(new_course)
    db.flush()  # get new_course.id without committing yet

    for lesson in old_course.lessons:
        db.add(Lesson(
            course_id=new_course.id,
            title=lesson.title,
            order_index=lesson.order_index,
            content_markdown=lesson.content_markdown,
            video_url=lesson.video_url,
            estimated_minutes=lesson.estimated_minutes,
            has_quiz=lesson.has_quiz,
            has_playground=lesson.has_playground,
            playground_starter_code=lesson.playground_starter_code,
            playground_language=lesson.playground_language,
            is_downloadable=lesson.is_downloadable,
        ))

    old_course.is_latest_version = False
    db.commit()
    db.refresh(new_course)
    return new_course

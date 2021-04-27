# |docname| - definition of database models
# *****************************************
# In this file we define our SQLAlchemy data models. These get translated into relational database tables.
#
# Because of the interface with the `databases package <https://www.encode.io/databases/>`_ we will use the `SQLAlchemy core API <https://docs.sqlalchemy.org/en/14/core/>`_
#
# Migrations
# ==========
# We use `Alembic <https://alembic.sqlalchemy.org/en/latest/>`_ for tracking database migration information.
# To create a new migration automatically after you have made changes to this file, run ``alembic revision --autogenerate -m "simple message"``
# this will generate a new file in ``alembic/versions``. To apply changes to the database run ``alembic upgrade head``.
#
# :index:`docs to write`: It is also possible...
#
# Imports
# =======
# These are listed in the order prescribed by `PEP 8`_.
#
# Standard library
# ----------------
# None.
#
# Third-party imports
# -------------------
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Date,
    DateTime,
    MetaData,
    Text,
    types,
    Float,
    inspect,
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql.schema import UniqueConstraint

# Local application imports
# -------------------------
# None.
from .db import Base


# Web2Py boolean type
# ===================
# Define a web2py-compatible Boolean type. See `custom types <http://docs.sqlalchemy.org/en/latest/core/custom_types.html>`_.
class Web2PyBoolean(types.TypeDecorator):
    impl = types.CHAR(1)

    def process_bind_param(self, value, dialect):
        if value:
            return "T"
        elif value is None:
            return None
        elif not value:
            return "F"
        else:
            assert False

    def process_result_value(self, value, dialect):
        if value == "T":
            return True
        elif value == "F":
            return False
        elif value is None:
            return None
        else:
            assert False

    def copy(self, **kw):
        return Web2PyBoolean(self.impl.length)


# Schema Definition
# =================
# this object is a container for the table objects and can be used by alembic to autogenerate
# the migration information.
metadata = MetaData()

answer_tables = {}


def register_answer_table(cls):
    global answer_tables
    answer_tables[cls.__tablename__] = cls
    return cls


# IdMixin
# -------
# Always name a table's ID field the same way.
class IdMixin:
    id = Column(Integer, primary_key=True)


# Useinfo
# -------
# This defines the useinfo table in the database.  This table logs nearly every click
# generated by a student.  It gets very large and needs a lot of indexes to keep Runestone
# from bogging down.
# Useinfo
# -------
# User info logged by the `hsblog endpoint`. See there for more info.
class Useinfo(Base, IdMixin):
    __tablename__ = "useinfo"
    # _`timestamp`: when this entry was recorded by this webapp.
    timestamp = Column(DateTime, index=True)
    # _`sid`: TODO: The student id? (user) which produced this row.
    sid = Column(String(512), index=True)
    # The type of question (timed exam, fill in the blank, etc.).
    event = Column(String(512), index=True)
    # TODO: What is this? The action associated with this log entry?
    act = Column(String(512))
    # _`div_id`: the ID of the question which produced this entry.
    div_id = Column(String(512), index=True)
    # _`course_id`: the Courses ``course_name`` **NOT** the ``id`` this row refers to. TODO: Use the ``id`` instead!
    course_id = Column(String(512), ForeignKey("courses.course_name"), index=True)
    # These are not currently in web2py but I'm going to add them
    chapter = Column(String, unique=False, index=False)
    sub_chapter = Column(String, unique=False, index=False)


# Questions
# ---------
# A question in the book; this data is provided by Sphinx.
class Questions(Base, IdMixin):
    __tablename__ = "questions"
    # The base_course_ this question is in.
    base_course = Column(String(512), nullable=False)
    # The div_id_ for this question. TODO: Rename this!
    name = Column(String(512), nullable=False, index=True)
    # matches chapter_label, not name
    chapter = Column(String(512))
    # matches sub_chapter_label, not name
    subchapter = Column(String(512))
    author = Column(String(512))
    difficulty = Column(Integer)
    question = Column(Text)
    timestamp = Column(DateTime)
    question_type = Column(String(512))
    is_private = Column(Web2PyBoolean)
    htmlsrc = Column(Text)
    autograde = Column(String(512))
    __table_args__ = (
        Index("idx_quests_chap_subchap", "chapter", "subchapter"),
        UniqueConstraint("name", "base_course", name="const_uniq_name_bc"),
    )


# Answers to specific question types
# ----------------------------------
# Many of the tables containing answers are always accessed by sid, div_id and course_name. Provide this as a default query.
class AnswerMixin(IdMixin):
    # TODO: these entries duplicate Useinfo.timestamp. Why not just have a timestamp_id field?
    #
    # See timestamp_.
    timestamp = Column(DateTime)
    # See div_id_.
    div_id = Column(String(512), index=True)
    # See sid_.
    sid = Column(String(512), index=True)

    # See course_name_. Mixins with foreign keys need `special treatment <http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/mixins.html#mixing-in-columns>`_.
    @declared_attr
    def course_name(cls):
        return Column(String(512), ForeignKey("courses.course_name"))

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}


class TimedExam(Base, AnswerMixin):
    __tablename__ = "timed_exam"
    # See the `timed exam endpoint parameters <timed exam>` for documenation on these columns.
    correct = Column(Integer)
    incorrect = Column(Integer)
    skipped = Column(Integer)
    time_taken = Column(Integer)
    # True if the ``act`` endpoint parameter was ``'reset'``; otherwise, False.
    reset = Column(Web2PyBoolean)


# Like an AnswerMixin, but also has a boolean correct_ field.
class CorrectAnswerMixin(AnswerMixin):
    # _`correct`: True if this answer is correct.
    correct = Column(Web2PyBoolean)
    percent = Column(Float)


# An answer to a multiple-choice question.
@register_answer_table
class MchoiceAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "mchoice_answers"
    # _`answer`: The answer to this question. TODO: what is the format?
    answer = Column(String(50))
    __table_args__ = (Index(f"idx_div_sid_course_mc", "sid", "div_id", "course_name"),)


# An answer to a fill-in-the-blank question.
@register_answer_table
class FitbAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "fitb_answers"
    # See answer_. TODO: what is the format?
    answer = Column(String(512))
    __table_args__ = (Index(f"idx_div_sid_course_fb", "sid", "div_id", "course_name"),)


# An answer to a drag-and-drop question.
@register_answer_table
class DragndropAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "dragndrop_answers"
    # See answer_. TODO: what is the format?
    answer = Column(String(512))
    __table_args__ = (Index(f"idx_div_sid_course_dd", "sid", "div_id", "course_name"),)


# An answer to a drag-and-drop question.
@register_answer_table
class ClickableareaAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "clickablearea_answers"
    # See answer_. TODO: what is the format?
    answer = Column(String(512))
    __table_args__ = (Index(f"idx_div_sid_course_ca", "sid", "div_id", "course_name"),)


# An answer to a Parsons problem.
@register_answer_table
class ParsonsAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "parsons_answers"
    # See answer_. TODO: what is the format?
    answer = Column(String(512))
    # _`source`: The source code provided by a student? TODO.
    source = Column(String(512))
    __table_args__ = (Index(f"idx_div_sid_course_pp", "sid", "div_id", "course_name"),)


# An answer to a Code Lens problem.
@register_answer_table
class CodelensAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "codelens_answers"
    # See answer_. TODO: what is the format?
    answer = Column(String(512))
    # See source_.
    source = Column(String(512))
    __table_args__ = (Index(f"idx_div_sid_course_cl", "sid", "div_id", "course_name"),)


@register_answer_table
class ShortanswerAnswers(Base, AnswerMixin):
    __tablename__ = "shortanswer_answers"
    # See answer_. TODO: what is the format?
    answer = Column(String(512))
    __table_args__ = (Index(f"idx_div_sid_course_sa", "sid", "div_id", "course_name"),)


@register_answer_table
class UnittestAnswers(Base, CorrectAnswerMixin):
    __tablename__ = "unittest_answers"
    answer = Column(Text)
    passed = Column(Integer)
    failed = Column(Integer)
    __table_args__ = (Index(f"idx_div_sid_course_ut", "sid", "div_id", "course_name"),)


@register_answer_table
class LpAnswers(Base, AnswerMixin):
    __tablename__ = "lp_answers"
    # See answer_. A JSON string; see RunestoneComponents for details. TODO: The length seems too short to me.
    answer = Column(String(512))
    # A grade between 0 and 100.
    correct = Column(Float())
    __table_args__ = (Index(f"idx_div_sid_course_lp", "sid", "div_id", "course_name"),)


# Code
# ----
# The code table captures every run/change of the students code.  It is used to load
# the history slider of the activecode component.
#
class Code(Base, IdMixin):
    __tablename__ = "code"
    timestamp = Column(DateTime, unique=False, index=True)
    sid = Column(String(512), unique=False, index=True)
    acid = Column(
        String(512),
        unique=False,
        index=True,
    )  # unique identifier for a component
    course_name = Column(String, index=True)
    course_id = Column(Integer, index=False)
    code = Column(Text, index=False)
    language = Column(Text, index=False)
    emessage = Column(Text, index=False)
    comment = Column(Text, index=False)


# Courses
# -------
# Every Course in the runestone system must have an entry in this table
# the id column is really an artifact of the original web2py/pydal implementation of
# Runestone.  The 'real' primary key of this table is the course_name
# Defines either a base course (which must be manually added to the database) or a derived course created by an instructor.
class Courses(Base, IdMixin):
    __tablename__ = "courses"
    # _`course_name`: The name of this course.
    course_name = Column(String(512), unique=True)
    term_start_date = Column(Date)
    # TODO: Why not use base_course_id instead? _`base_course`: the course from which this course was derived. TODO: If this is a base course, this field should be identical to the course_name_?
    base_course = Column(String(512), ForeignKey("courses.course_name"))
    # TODO: This should go in a different table. Not all courses have a Python/Skuplt component.
    login_required = Column(Web2PyBoolean)
    allow_pairs = Column(Web2PyBoolean)
    student_price = Column(Integer)
    downloads_enabled = Column(Web2PyBoolean)
    courselevel = Column(String)

    # # Create ``child_courses`` which all refer to a single ``parent_course``: children's ``base_course`` matches a parent's ``course_name``. See `adjacency list relationships <http://docs.sqlalchemy.org/en/latest/orm/self_referential.html#self-referential>`_.
    # child_courses = relationship(
    #
    #     "Courses", backref=backref("parent_course", remote_side=[course_name])
    # )

    # Define a default query: the username if provided a string. Otherwise, automatically fall back to the id.
    @classmethod
    def default_query(cls, key):
        if isinstance(key, str):
            return cls.course_name == key


class AuthUser(Base, IdMixin):
    __tablename__ = "auth_user"
    username = Column(String(512), nullable=False, unique=True)
    first_name = Column(String(512))
    last_name = Column(String(512))
    email = Column(String(512), unique=True)
    password = Column(String(512))
    created_on = Column(DateTime())
    modified_on = Column(DateTime())
    registration_key = Column(String(512))
    reset_password_key = Column(String(512))
    registration_id = Column(String(512))
    course_id = Column(Integer)
    course_name = Column(String(512))
    active = Column(Web2PyBoolean)
    donated = Column(Web2PyBoolean)
    accept_tcp = Column(Web2PyBoolean)

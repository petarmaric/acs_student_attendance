About
=====

Console app and Python API for analyzing and reporting the lab attendance of our
`ACS`_ students.

.. _`ACS`: http://www.acs.uns.ac.rs/


Installation
============

To install acs_student_attendance run::

    $ pip install acs_student_attendance


Console app usage
=================

Quick start::

    $ acs_student_attendance stud_auth.log semester-config.yml

Show help::

    $ acs_student_attendance --help


Python API usage
================

Quick start::

    >>> from acs_student_attendance.analysis import StudentAttendanceAnalysisWithExport
    >>> log_lines = open('stud_auth.log')
    >>> analyzer = StudentAttendanceAnalysisWithExport('semester-config.yml')
    >>> results = analyzer(log_lines)


Contribute
==========

If you find any bugs, or wish to propose new features `please let us know`_.

If you'd like to contribute, simply fork `the repository`_, commit your changes
and send a pull request. Make sure you add yourself to `AUTHORS`_.

.. _`please let us know`: https://github.com/petarmaric/acs_student_attendance/issues/new
.. _`the repository`: https://github.com/petarmaric/acs_student_attendance
.. _`AUTHORS`: https://github.com/petarmaric/acs_student_attendance/blob/master/AUTHORS

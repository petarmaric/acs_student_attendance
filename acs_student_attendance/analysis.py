from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
import os
import shutil

import tablib
import yaml

from . import DEFAULT_OUTPUT_DIR
from .log_parser import StudentAuthLogParser, remove_fields, replace_field, transform_field


def needs_semester_config(func):
    @wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    
    inner.needs_semester_config = True    
    return inner

def weeknumber(dt):
    return dt.isocalendar()[1]


class StudentAttendanceAnalysis(object):
    _weekday_list = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    _weekday_to_int = {day: num for num, day in enumerate(_weekday_list, start=1)}

    log_parser_cls = StudentAuthLogParser

    def _filter_logins(self, parsed_log_lines):
        """
        We're only interested when have the students 'opened' their session,
        aka 'logged in'
        """
        return (line for line in parsed_log_lines if line['session_action'] == 'opened')

    @needs_semester_config
    def _apply_schedule_overrides(self, parsed_log_lines):
        """
        Apply lab schedule overrides, for every holiday date in this semester
        """
        def inner(dt):
            for override in self.semester_config['semester'].get('schedule_overrides', []):
                if dt.date() == override['completed_on']:
                    return datetime.combine(
                        date=override['holiday_date'],
                        time=dt.time()
                    )

            # No matching schedule overrides found
            return dt

        return transform_field(parsed_log_lines, 'datetime', inner)

    def _remove_unnecessary_fields(self, parsed_log_lines):
        """
        Removes any fields we don't need for further analysis
        """
        return remove_fields(parsed_log_lines, ['computer_id', 'session_action'])

    def _break_apart_datetime_field(self, parsed_log_lines):
        """
        Breaks apart the 'datetime' field into multiple `datetime` related
        components, which will be more suitable for further analysis
        """
        return replace_field(parsed_log_lines, 'datetime', lambda dt: {
            'year': dt.year,
            'weeknumber': weeknumber(dt),
            'weekday': dt.isoweekday(),
            'date': dt.date(),
            'time': dt.time(),
        })

    extra_log_transformation_pipeline = [
        _filter_logins,
        _apply_schedule_overrides,
        _remove_unnecessary_fields,
        _break_apart_datetime_field,
    ]

    def __init__(self, semester_config, log_parser=None,
        override_log_transformation_pipeline=None):

        if isinstance(semester_config, (str, unicode)):
            with open(semester_config) as fp:
                semester_config = yaml.load(fp)

                # When a `semester_config` object is loaded from a YAML file its
                # `extra_settings:student_login_time_spread` value is decoded as
                # a Python `int`, due to YAML limitations.
                # Convert it manually to a proper `timedelta` object before use.
                extra_settings = semester_config.get('extra_settings', {})
                if 'student_login_time_spread' in extra_settings:
                    extra_settings['student_login_time_spread'] = timedelta(
                        seconds=extra_settings['student_login_time_spread']
                    )

                # When a `semester_config` object is loaded from a YAML file its
                # lab schedule terms are 'string-encoded', due to YAML limitations.
                # Convert them manually to proper `datetime` objects before use.
                for course_data in semester_config.get('courses', {}).values():
                    weekly_lab_schedule = course_data.get('weekly_lab_schedule', {})
                    for weekday_name, terms in weekly_lab_schedule.items():
                        weekly_lab_schedule[weekday_name] = [
                            [
                                datetime.strptime(part.strip(), "%H:%M").time()
                                for part in term.split('-')
                            ]
                            for term in terms
                        ]

        self.semester_config = semester_config

        self.log_parser = log_parser or self.log_parser_cls()

        if override_log_transformation_pipeline:
            self.extra_log_transformation_pipeline = []
            self.log_parser.log_transformation_pipeline = override_log_transformation_pipeline

        new_pipeline = self.log_parser.log_transformation_pipeline + self.extra_log_transformation_pipeline
        self.log_parser.log_transformation_pipeline = new_pipeline

        someone_needs_semester_config = any(
            getattr(transformation, 'needs_semester_config', False)
            for transformation in self.log_parser.log_transformation_pipeline
        )
        if someone_needs_semester_config:
            # If true, at least one transformation requires `semester_config` to
            # function properly.
            # However, `self.log_parser.log_transformation_pipeline` is always
            # executed in the context of `self.log_parser`, which by default has
            # no access to `self.semester_config`.
            #
            # Thus, we inject `self.semester_config` into `self.log_parser`.
            self.log_parser.semester_config = self.semester_config
    
    @property
    def weekday_terms(self):
        if not hasattr(self, '_weekday_terms'):
            extra_settings = self.semester_config.get('extra_settings', {})
            login_time_spread = extra_settings.get('student_login_time_spread', timedelta(0))

            if not login_time_spread:
                expand_term_interval = lambda term: term # noop, for speed
            else:
                _cached_today = datetime.today()
                def add_time(time, delta): # Can't add `time` and `timedelta` in Python
                    return (datetime.combine(date=_cached_today, time=time) + delta).time()

                def expand_term_interval(term):
                    start_time, end_time = term
                    return [
                        add_time(start_time, -login_time_spread),
                        add_time(end_time,    login_time_spread),
                    ]

            self._weekday_terms = defaultdict(list)
            for course_name, course_data in self.semester_config.get('courses', {}).items():
                for weekday_name, terms in course_data.get('weekly_lab_schedule', {}).items():
                    weekday = self._weekday_to_int[weekday_name.lower()]
                    self._weekday_terms[weekday].extend(
                        [course_name] + expand_term_interval(term)
                        for term in terms
                    )

        return self._weekday_terms

    @property
    def semester_weeks(self):
        if not hasattr(self, '_semester_weeks'):
            start = self.semester_config['semester']['start_date']
            end = self.semester_config['semester']['end_date']

            self._semester_weeks = []
            while start <= end:
                self._semester_weeks.append((start.year, weeknumber(start)))
                start += timedelta(days=7)

        return self._semester_weeks

    @property
    def report_fields(self):
        if not hasattr(self, '_report_fields'):
            self._report_fields = ['student id'] + [
                "week %02d" % idx
                for idx, _ in enumerate(self.semester_weeks, start=1)
            ] + ['total']

        return self._report_fields
   
    def _init_attendance_list(self):
        return [0] * len(self.semester_weeks)

    def _get_attendance_list_index(self, login):
        return bisect_left(self.semester_weeks, (login['year'], login['weeknumber']))

    def analyze(self, log_lines):
        parsed_log_lines = self.log_parser(log_lines)
        
        semester_start_date = self.semester_config['semester']['start_date']
        semester_end_date = self.semester_config['semester']['end_date']

        courses = self.semester_config.get('courses', {})
        student_attendance = {
            course_name: defaultdict(self._init_attendance_list)
            for course_name in courses
        }

        for login in parsed_log_lines:
            for course_name, start_time, end_time in self.weekday_terms.get(login['weekday'], []):
                if semester_start_date <= login['date'] <= semester_end_date:
                    if start_time <= login['time'] <= end_time:
                        attendance_list = student_attendance[course_name][login['student_id']]
                        attendance_list[self._get_attendance_list_index(login)] = 1

        results = tablib.Databook()
        for course_name, students in student_attendance.items():
            dataset = tablib.Dataset(headers=self.report_fields)

            dataset.title = course_name
            dataset.teacher = courses[course_name]['teacher']

            dataset.extend(
                [student] + attendance_list + [sum(attendance_list)]
                for student, attendance_list in sorted(students.items())
            )

            results.add_sheet(dataset)
        
        return results
    
    def __call__(self, log_lines):
        return self.analyze(log_lines)


class StudentAttendanceAnalysisWithExport(StudentAttendanceAnalysis):
    output_dir = None

    report_file_formats = ['csv', 'html', 'json', 'tsv', 'xls', 'xlsx', 'yaml']

    def __init__(self, semester_config, log_parser=None,
        override_log_transformation_pipeline=None, output_dir=None,
        report_file_formats=None):
        super(StudentAttendanceAnalysisWithExport, self).__init__(
            semester_config=semester_config,
            log_parser=log_parser,
            override_log_transformation_pipeline=override_log_transformation_pipeline
        )
        
        if output_dir:
            self.output_dir = output_dir
        
        if not self.output_dir: 
            self.output_dir = DEFAULT_OUTPUT_DIR
        
        if report_file_formats:
            self.report_file_formats = report_file_formats
    
    def save_results(self, results):
        if os.path.exists(self.output_dir):
            print "Directory '%s' already exists and will be deleted before continuing." % self.output_dir
            shutil.rmtree(self.output_dir)

        for dataset in results.sheets():
            print "Saving analysis results for '%s':" % dataset.title
            
            dataset.results_dir = os.path.join(self.output_dir, dataset.teacher)
            if not os.path.exists(dataset.results_dir):
                os.makedirs(dataset.results_dir)

            for fmt in tablib.formats.available:
                if fmt.title not in self.report_file_formats:
                    continue # Skip the formats we're not interested in

                try:
                    results_filename = os.path.join(
                        dataset.results_dir,
                        "%s.%s" % (dataset.title, fmt.title)
                    )
                    print "\t%s..." % results_filename,

                    with open(results_filename, 'wb') as out:
                        out.write(fmt.export_set(dataset))

                    print 'OK!'
                except Exception, e:
                    print 'ERROR:', e
    
    def analyze_and_save_results(self, log_lines):
        print 'Analyzing the student auth logs, this might take a while...',
        results = self.analyze(log_lines)
        print 'DONE!'

        self.save_results(results)
        return results
    
    def __call__(self, log_lines):
        return self.analyze_and_save_results(log_lines)

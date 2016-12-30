import argparse

from . import __version__, DEFAULT_OUTPUT_DIR
from .analysis import StudentAttendanceAnalysisWithExport


def main():
    # Setup command line option parser
    parser = argparse.ArgumentParser(
        prog='acs_student_attendance',
        description='Analyzes and reports the lab attendance of our ACS students'
    )
    parser.add_argument(
        'auth_log_filename',
        metavar='auth-log',
        help='Student auth log file, as provided by our ACS administrators'
    )
    parser.add_argument(
        'semester_config_filename',
        metavar='semester-config',
        help="YAML file describing the semester to analyze, please see "\
             "'samples/semester-config.yml' for an example"
    )
    parser.add_argument(
        '-o',
        '--output-to',
        metavar='<directory>',
        default=DEFAULT_OUTPUT_DIR,
        help="Output the attendance reports to selected <directory>, '%s' by default" % DEFAULT_OUTPUT_DIR
    )
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s " + __version__
    )
    args = parser.parse_args()

    log_lines = open(args.auth_log_filename)
    StudentAttendanceAnalysisWithExport(
        semester_config=args.semester_config_filename,
        output_dir=args.output_to
    ).analyze_and_save_results(log_lines)

    print 'DONE!'

if __name__ == '__main__':
    main()

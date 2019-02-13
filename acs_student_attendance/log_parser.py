from datetime import datetime
import re
import string


def transform_field(dictseq, key, transform_function):
    """
    Generator that takes a sequence of dictionaries and transforms one of
    the fields in every dictionary using the provided `transform_function`
    """
    for d in dictseq:
        d[key] = transform_function(d[key])
        yield d

def replace_field(dictseq, key, replace_function):
    """
    Generator that takes a sequence of dictionaries and replaces one of the
    fields in every dictionary with the fields provided by `replace_function`
    """
    for d in dictseq:
        d.update(replace_function(d.pop(key)))
        yield d

def remove_fields(dictseq, keys):
    """
    Generator that takes a sequence of dictionaries and removes the given
    fields from every dictionary
    """
    for d in dictseq:
        for key in keys:
            d.pop(key)
        yield d


class StudentAuthLogParser(object):
    log_format_re = re.compile(
        r'(?P<datetime>.+?) 192.168.18.(?P<computer_id>\d{3}) '
        r'lightdm: pam_unix\(lightdm:session\): session (?P<session_action>[a-z]+) '
        r'for user\s+(?P<student_id>\S+)\s*(?:by \(uid=\d+\))?$'
    )

    def _transform_datetime_field(self, parsed_log_lines):
        """
        Transforms the 'datetime' field to a proper `datetime` object
        """
        return transform_field(parsed_log_lines, 'datetime', self._parse_datetime)

    def _transform_computer_id_field(self, parsed_log_lines):
        """
        Transforms the 'computer_id' field to our 'sXYZ' computer id format
        """
        return transform_field(parsed_log_lines, 'computer_id', lambda x: 's'+x)

    def _transform_student_id_field(self, parsed_log_lines):
        """
        Transforms the 'student_id' field to a normalized (lowercase) string
        """
        return transform_field(parsed_log_lines, 'student_id', string.lower)

    log_transformation_pipeline = [
        _transform_datetime_field,
        _transform_computer_id_field,
        _transform_student_id_field,

    ]

    def _parse_datetime(self, datetime_str):
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    def _transform_log_lines(self, parsed_log_lines):
        for transformation in self.log_transformation_pipeline:
            parsed_log_lines = transformation(self, parsed_log_lines)

        return parsed_log_lines

    def _gen_parsed_log_lines(self, lines):
        """
        Generator that looks for lines matching the log format and yields a
        sequence of matches, organized into dictionaries
        """
        for line in lines:
            match = self.log_format_re.match(line)
            if match:
                yield match.groupdict()
            else:
                print 'Unknown line found while parsing:', line[:-1]

    def parse(self, log_lines):
        """
        Generator that takes an iterable containing log lines and parses them
        into a sequence of dictionaries
        """
        parsed_log_lines = self._gen_parsed_log_lines(log_lines)
        parsed_log_lines = self._transform_log_lines(parsed_log_lines)
        return parsed_log_lines

    def __call__(self, log_lines):
        return self.parse(log_lines)

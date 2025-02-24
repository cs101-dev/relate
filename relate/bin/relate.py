#! /usr/bin/env python3

import sys
import io


def validate(args):
    from django.conf import settings
    settings.configure(DEBUG=True)

    import django
    django.setup()

    from course.validation import validate_course_on_filesystem
    has_warnings = validate_course_on_filesystem(args.REPO_ROOT,
            course_file=args.course_file,
            events_file=args.events_file)

    if has_warnings and args.warn_error:
        return 1
    else:
        return 0


# {{{ expand YAML

def expand_yaml(yml_file, repo_root):
    if yml_file == "-":
        data = sys.stdin.read()
    else:
        with open(yml_file) as inf:
            data = inf.read()

    from course.content import (
            process_yaml_for_expansion, YamlBlockEscapingFileSystemLoader)
    data = process_yaml_for_expansion(data)

    from jinja2 import Environment, StrictUndefined
    jinja_env = Environment(
            loader=YamlBlockEscapingFileSystemLoader(repo_root),
            undefined=StrictUndefined)
    template = jinja_env.from_string(data)
    data = template.render()

    return data

# }}}


# {{{ code test

def test_code_question(page_desc, repo_root):
    if page_desc.type not in [
            "PythonCodeQuestion",
            "PythonCodeQuestionWithHumanTextFeedback",
            "OctaveCodeQuestion"]:
        return

    print(75*"-")
    print("TESTING", page_desc.id, "...", end=" ")
    sys.stdout.flush()

    test_code = getattr(page_desc, "test_code", None)
    if test_code is not None:

        correct_code = getattr(page_desc, "correct_code", "")

        from course.page.code_run_backend import \
                substitute_correct_code_into_test_code
        test_code = substitute_correct_code_into_test_code(test_code, correct_code)

    from course.page.code_run_backend import run_code, package_exception

    data_files = {}

    for data_file_name in getattr(page_desc, "data_files", []):
        from base64 import b64encode
        with open(data_file_name, "rb") as df:
            data_files[data_file_name] = b64encode(df.read()).decode()

    run_req = {
            "setup_code": getattr(page_desc, "setup_code", ""),
            "names_for_user": getattr(page_desc, "names_for_user", []),
            "user_code": (
                getattr(page_desc, "check_user_code", "")
                or getattr(page_desc, "correct_code", "")),
            "names_from_user": getattr(page_desc, "names_from_user", []),
            "test_code": test_code,
            "data_files": data_files,
            }

    response = {}

    prev_stdin = sys.stdin  # noqa
    prev_stdout = sys.stdout  # noqa
    prev_stderr = sys.stderr  # noqa

    stdout = io.StringIO()
    stderr = io.StringIO()

    from time import time
    start = time()

    try:
        sys.stdin = None
        sys.stdout = stdout
        sys.stderr = stderr

        from relate.utils import Struct
        run_code(response, Struct(run_req))

        response["stdout"] = stdout.getvalue()
        response["stderr"] = stderr.getvalue()

    except Exception:
        response = {}
        package_exception(response, "uncaught_error")

    finally:
        sys.stdin = prev_stdin
        sys.stdout = prev_stdout
        sys.stderr = prev_stderr

    stop = time()
    response["timeout"] = (
            "Execution took %.1f seconds. "
            "(Timeout is %.1f seconds.)"
            % (stop-start, page_desc.timeout))

    from colorama import Fore, Style
    if response["result"] == "success":
        points = response.get("points", 0)
        if points is None:
            print(Fore.RED
                    + "FAIL: no points value recorded"
                    + Style.RESET_ALL)
        elif points < 1:
            print(Fore.RED
                    + "FAIL: code did not pass test"
                    + Style.RESET_ALL)
        else:
            print(Fore.GREEN+response["result"].upper()+Style.RESET_ALL)
    else:
        print(Style.BRIGHT+Fore.RED
                + response["result"].upper()+Style.RESET_ALL)

    def print_response_aspect(s):
        if s not in response:
            return

        if isinstance(response[s], list):
            response_s = "\n".join(str(s_i) for s_i in response[s])
        else:
            response_s = str(response[s]).strip()

        if not response_s:
            return

        print(s, ":")
        indentation = 4*" "
        print(indentation + response_s.replace("\n", "\n"+indentation))

    print_response_aspect("points")
    print_response_aspect("feedback")
    print_response_aspect("traceback")
    print_response_aspect("stdout")
    print_response_aspect("stderr")
    print_response_aspect("timeout")


def test_code_yml(yml_file, repo_root):
    data = expand_yaml(yml_file, repo_root)

    from yaml import safe_load
    from relate.utils import dict_to_struct
    data = dict_to_struct(safe_load(data))

    if hasattr(data, "id") and hasattr(data, "type"):
        test_code_question(data, repo_root)

    else:
        if hasattr(data, "groups"):
            pages = [
                    page
                    for grp in data.groups
                    for page in grp.pages]
        elif hasattr(data, "pages"):
            pages = data.pages
        else:
            from colorama import Fore, Style
            print(Fore.RED + Style.BRIGHT
                    + "'%s' does not look like a valid flow or page file"
                    % yml_file
                    + Style.RESET_ALL)
            return

        for page in pages:
            test_code_question(page, repo_root)


def test_code(args):
    for yml_file in args.FLOW_OR_PROBLEM_YMLS:
        print(75*"=")
        print("EXAMINING", yml_file)
        test_code_yml(yml_file, repo_root=args.repo_root)

    return 0

# }}}


def expand_yaml_ui(args):
    print(expand_yaml(args.YAML_FILE, args.repo_root))


def main() -> None:
    pass
    import os
    import argparse

    os.environ["RELATE_COMMAND_LINE"] = "1"

    parser = argparse.ArgumentParser(
            description="RELATE course content command line tool")
    subp = parser.add_subparsers()

    parser_validate = subp.add_parser("validate")
    parser_validate.add_argument("--course-file", default="course.yml")
    parser_validate.add_argument("--events-file", default="events.yml")
    parser_validate.add_argument("--warn-error", action="store_true",
            help="Treat warnings as errors")
    parser_validate.add_argument("REPO_ROOT", default=os.getcwd())
    parser_validate.set_defaults(func=validate)

    parser_test_code = subp.add_parser("test-code")
    parser_test_code.add_argument("--repo-root", default=os.getcwd())
    parser_test_code.add_argument("FLOW_OR_PROBLEM_YMLS", nargs="+")
    parser_test_code.set_defaults(func=test_code)

    parser_expand_yaml = subp.add_parser("expand-yaml")
    parser_expand_yaml.add_argument("--repo-root", default=os.getcwd())
    parser_expand_yaml.add_argument("YAML_FILE")
    parser_expand_yaml.set_defaults(func=expand_yaml_ui)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_usage()
        import sys
        sys.exit(1)

    import sys
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

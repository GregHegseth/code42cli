from argparse import ArgumentParser
from datetime import datetime, timedelta
from keyring import get_password, set_password
from getpass import getpass
import urllib3
import configparser

from py42.sdk import SDK
import py42.debug_level as debug_level
from py42 import settings
from c42secevents.extractors import AEDEventExtractor
from c42secevents.common import FileEventHandlers

from c42seceventcli.common.common import parse_timestamp, convert_date_to_timestamp
from c42seceventcli.aed.aed_cursor_store import AEDCursorStore
from c42seceventcli.common.cli_args import (
    add_authority_host_address_arg,
    add_username_arg,
    add_begin_timestamp_arg,
    add_help_arg,
    add_ignore_ssl_errors_arg,
    add_output_format_arg,
    add_end_timestamp_arg,
    add_record_cursor_arg,
    add_exposure_type_args,
    add_debug_arg,
)

_SERVICE_NAME_FOR_KEYCHAIN = u"c42seceventcli"


def main():
    parser = _get_arg_parser()
    args = parser.parse_args()

    if args.c42_ignore_ssl_errors:
        _ignore_ssl_errors()

    if args.c42_debug_mode:
        settings.debug_level = debug_level.DEBUG

    # Must either pass in a username and server address or provide them in config.cfg.
    config = _get_config()
    if config:
        username = config.get("username")
        server = config.get("server")
    else:
        username = args.c42_username
        server = args.c42_authority_url

    if server is None:
        _exit_from_argument_error("Host address not provided.", parser)

    if username is None:
        _exit_from_argument_error("Username not provided.", parser)

    password = _get_password(username)

    min_timestamp = parse_timestamp(args.c42_begin_date)
    max_timestamp = parse_timestamp(args.c42_end_date)

    if not _verify_min_timestamp(min_timestamp):
        print("Argument --begin must be within 90 days")
        exit(1)

    sdk = SDK.create_using_local_account(host_address=server, username=username, password=password)
    handlers = _create_handlers(args.c42_output_format)
    extractor = AEDEventExtractor(sdk, handlers)
    extractor.extract(min_timestamp, max_timestamp, args.c42_exposure_types)


def _get_arg_parser():
    parser = ArgumentParser(add_help=False)

    # Makes sure that you can't give both an end_timestamp and record cursor positions
    mutually_exclusive_timestamp_group = parser.add_mutually_exclusive_group()
    add_end_timestamp_arg(mutually_exclusive_timestamp_group)
    add_record_cursor_arg(mutually_exclusive_timestamp_group)

    main_args = parser.add_argument_group("main")
    add_authority_host_address_arg(main_args)
    add_username_arg(main_args)
    add_help_arg(main_args)
    add_begin_timestamp_arg(main_args)
    add_ignore_ssl_errors_arg(main_args)
    add_output_format_arg(main_args)
    add_exposure_type_args(main_args)
    add_debug_arg(main_args)
    return parser


def _ignore_ssl_errors():
    settings.verify_ssl_certs = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_password(username):
    password = get_password(_SERVICE_NAME_FOR_KEYCHAIN, username)
    if password is None:
        pwd = getpass()
        set_password(_SERVICE_NAME_FOR_KEYCHAIN, username, pwd)

    return password


def _verify_min_timestamp(min_timestamp):
    boundary_date = datetime.utcnow() - timedelta(days=90)
    boundary = convert_date_to_timestamp(boundary_date)
    return min_timestamp >= boundary


def _create_handlers(output_type):
    store = AEDCursorStore()
    handlers = FileEventHandlers()
    handlers.record_cursor_position = store.replace_stored_insertion_timestamp
    handlers.get_cursor_position = store.get_stored_insertion_timestamp
    handlers.handle_response = _get_response_handler(output_type)
    return handlers


def _get_response_handler(output_format):
    def handle_response(response):
        print(response.text)
        # TODO: Replace with logging from Alan's branch

    return handle_response


def _get_config():
    config = configparser.ConfigParser()
    config_file_found = len(config.read("config.cfg")) > 0
    return config["Code42"] if config_file_found else None


def _exit_from_argument_error(message, parser):
    print(message)
    parser.print_usage()
    exit(1)


if __name__ == "__main__":
    main()

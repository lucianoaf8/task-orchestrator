import orchestrator.cli as cli


def test_create_parser_schedule_options():
    parser = cli.create_parser()
    args = parser.parse_args(["schedule", "--list"])
    assert args.command == "schedule" and args.list


def test_create_parser_migrate_cleanup():
    parser = cli.create_parser()
    args = parser.parse_args(["migrate", "--cleanup"])
    assert args.command == "migrate" and args.cleanup


def test_create_parser_web_alias():
    parser = cli.create_parser()
    args = parser.parse_args(["web"])
    assert args.command == "web"

from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from reports.fetch import (
    fetch_stock_reports,
    calculate_hit_rate_of_report,
    calculate_hit_rate_of_analyst,
)
from reports.models import Report


class Command(BaseCommand):
    help = "Scrape stock reports related data from Naver and save to DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            "--file",
            type=str,
            help="File containing stock names, one per line",
        )
        parser.add_argument(
            "-s",
            "--stocks",
            nargs="+",
            type=str,
            help="List of stock names to scrape with spaces in between(ex. 삼성전자 카카오)",
        )
        parser.add_argument(
            "-c",
            "--calculate",
            nargs="+",
            type=str,
            help="Type either report or analyst that needs to be calculated",
        )
        parser.add_argument(
            "-m",
            "--max-reports-num",
            nargs="+",
            type=int,
            help="Maximum number of reports per stock to scrape",
            default=-1,
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        stocks = options["stocks"]
        calculate = options["calculate"]
        max_reports_num = options["max_reports_num"]

        if isinstance(max_reports_num, list):
            max_reports_num = max_reports_num[0]  # vs code debug issue

        if file_path:
            path = Path(file_path)
            if not path.is_file():
                raise CommandError(
                    f"File does not exist at the specified path: {file_path}"
                )

            with path.open(encoding="utf-8") as f:
                for line in f:
                    stock_name = line.strip()
                    if len(stock_name) == 0:
                        continue
                    fetch_stock_reports(stock_name, max_reports_num=max_reports_num)

        elif stocks:
            for stock_name in stocks:
                fetch_stock_reports(stock_name, max_reports_num=max_reports_num)

        elif calculate:
            if calculate[0] == "report":
                calculate_hit_rate_of_report()

            elif calculate[0] == "analyst":
                calculate_hit_rate_of_analyst()

        else:
            raise CommandError("Provide one of --file, --stocks, --calculate argument.")

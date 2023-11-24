from decimal import Decimal
import os
import openai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET  ## XML 데이터 파싱을 위한 패키지
from django.db.models import Count, Sum
from analyzer.analyze import analyze_pdf

from reports.models import Analyst, Currency, Point, Report, Stock, Writes


## stock : 주식 이름
## date : 원하는 날짜 (string type)
def get_price_on_publish(stock, date):
    # TODO: 어떤 주식이 어떤 날에 마감가가 얼마였는지 리턴
    # stock.name이나 stock.code가 채워져있을 것을 요구

    stockPriceApiBaseurl = os.getenv("STOCK_PRICE_API_BASE_URL")

    params = {
        "serviceKey": os.getenv("STOCK_PRICE_SERVICE_KEY"),
        "numOfRows": "365",  ## 검색 일수
        "itmsNm": stock.name,  ## 종목 이름
        "basDt": date.strftime("%Y%m%d"),  ## 검색 시작 날짜
    }

    ##print(stock.name)
    ##print(date.strftime('%Y%m%d'))

    try:
        ## GET 요청 보내기
        response = requests.get(stockPriceApiBaseurl, params=params)
        if response.status_code != 200:
            print(f"failed to get price of stock. GET failed {stockPriceApiBaseurl}")
            return None

        ## XML로 반환된 데이터의 내용 추출하기 위한 처리
        xml_data = response.content
        root = ET.fromstring(xml_data)

        # clpr(종가) 요소 추출
        price = root.find(".//clpr")
        price = price.text

        return price

    except Exception as e:
        print(f"너가 마주한 에러 : {e}")
        return None


## parameter : 주식 이름 (String type)
## return value : 주식 번호 (String type)
def get_stock_code(stock_name):
    # TODO: 공개된 API 등 이용해서 stock name -> stock code 변환 실행

    stockPriceApiBaseurl = os.getenv("STOCK_PRICE_API_BASE_URL")

    params = {
        "serviceKey": os.getenv("STOCK_PRICE_SERVICE_KEY"),
        "numOfRows": "1",  ## 검색 일수
        "itmsNm": stock_name,  ## 종목 이름
    }

    try:
        ## GET 요청 보내기
        response = requests.get(stockPriceApiBaseurl, params=params)
        if response.status_code != 200:
            print(f"failed to get stock code. GET failed {stockPriceApiBaseurl}")
            return None

        ## XML로 반환된 데이터의 내용 추출하기 위한 처리
        xml_data = response.content
        root = ET.fromstring(xml_data)

        # srtnCd(주식 번호) 요소 추출
        stock_code = root.find(".//srtnCd").text

        return stock_code

    except Exception as e:
        print(f"Error : {e}")
        return None

    # conversion = {
    #     "삼성전자": "005930",
    #     "카카오": "035720",
    #     "현대차": "005380",
    #     "현대자동차": "005380",
    #     "NAVER": "035420",
    #     "SK하이닉스": "000660",
    # }


## yyyy-mm-dd를 yyyymmdd로 변환
def date_to_text(date_object):
    date_string = date_object.replace("-", "")
    return date_string


def text_to_date(date_string):
    # "yy.mm.dd"를 파이썬 날짜 객체로 변경한다.
    if not date_string:
        return None

    # we assume that '23' refers to 2023.
    date_string = "20" + date_string
    date_object = datetime.strptime(date_string, "%Y.%m.%d").date()

    return date_object


def get_hidden_sentiment(report, analysts):
    # 리포트와 리포트를 쓴 애널리스트의 목록을 받아 같은 종목에 관해 같은 애널리스트들이 쓴 가장 가까운 과거의 리포트를 찾아 목표가를 비교한다.
    # 목표가가 하향됐으면 'SELL', 유지 또는 상향됐으면 'BUY'로 설정한다.
    # 바로 다음의 리포트에도 같은 방식을 적용해 업데이트해준다.

    last_report = (
        Report.objects.filter(
            stock=report.stock,
            writes__analyst__in=analysts,
            publish_date__lt=report.publish_date,
        )
        .order_by("publish_date")
        .last()
    )

    print(f"last report of {report} is {last_report}")

    hidden_sentiment = ""
    if last_report:
        if last_report.target_price < report.target_price:
            hidden_sentiment = "BUY"
        else:
            hidden_sentiment = "SELL"

    next_report = (
        Report.objects.filter(
            stock=report.stock,
            writes__analyst__in=analysts,
            publish_date__gt=report.publish_date,
        )
        .order_by("publish_date")
        .first()
    )

    print(f"next report of {report} is {next_report}")

    if next_report:
        if report.target_price < next_report.target_price:
            next_report.hidden_sentiment = "BUY"
        else:
            next_report.hidden_sentiment = "SELL"

        next_report.save()

    return hidden_sentiment


def get_next_publish_date(report, analysts):
    # 리포트와 리포트를 쓴 애널리스트의 목록을 받아 같은 종목에 관해 같은 애널리스트들이 쓴 가장 가까운 과거의 리포트를 찾아 is_newest, next_publish_date를 바꿔준다.
    # 이 리포트의 바로 다음 리포트를 찾아 다음 리포트의 존재여부, 존재한다면 publish_date에 따라 is_newest, next_publish_date를 업데이트한다.

    last_report = (
        Report.objects.filter(
            stock=report.stock,
            writes__analyst__in=analysts,
            publish_date__lt=report.publish_date,
        )
        .order_by("publish_date")
        .last()
    )

    if last_report:
        last_report.is_newest = False
        last_report.next_publish_date = report.publish_date
        last_report.save()

    next_report = (
        Report.objects.filter(
            stock=report.stock,
            writes__analyst__in=analysts,
            publish_date__gt=report.publish_date,
        )
        .order_by("publish_date")
        .first()
    )

    if next_report:
        return next_report.publish_date
    else:
        return None


def get_report_detail_info(report_detail_page_url):
    # report_detail_page_url를 스크레이핑해 목표가, sentiment를 tuple에 담아 리턴

    if not report_detail_page_url:
        return None

    response = requests.get(report_detail_page_url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")

    target_price = None
    written_sentiment = None

    money_elem = soup.select_one("em.money")
    if money_elem is not None:
        text = money_elem.text.replace(",", "")  # remove comma
        try:
            target_price = float(text)
        except ValueError:
            return None

    comment_elem = soup.select_one("em.coment")  # 'coment' 오타 아님
    if comment_elem is not None:
        written_sentiment = comment_elem.text

    if target_price is not None and written_sentiment is not None:
        written_sentiment = written_sentiment.strip().upper()
        if written_sentiment in ["BUY", "매수", "OUTPERFORM"]:
            written_sentiment = "BUY"
        elif written_sentiment in ["SELL", "매도"]:
            written_sentiment = "SELL"
        else:
            written_sentiment = "HOLD"

        return (target_price, written_sentiment)

    return None


def fetch_stock_reports(stock_name, currency="KRW", max_reports_num=-1):
    # Get stock code from stock name
    stock_code = get_stock_code(stock_name)
    if stock_code is None:
        return None

    # Create and save Stock instance
    try:
        currency_instance = Currency.objects.get(code=currency.upper())
    except Currency.DoesNotExist:
        print(
            f"Currency with code: {currency} does not exists in database(Unsupported currency yet)"
        )
        return None
    stock, _ = Stock.objects.get_or_create(
        name=stock_name, code=stock_code, currency=currency_instance
    )

    saved_reports_num = 0
    page_num = 1

    while max_reports_num == -1 or saved_reports_num < max_reports_num:
        url = f"https://finance.naver.com/research/company_list.naver?keyword=&brokerCode=&writeFromDate=&writeToDate=&searchType=itemCode&itemCode={stock_code}&page={page_num}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"failed to get reports list page. GET failed for {url}")
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the reports table
        reports_table = soup.select_one("div#contentarea table")

        # Iterate over each row in the table body (skipping header and empty rows)
        for row in reports_table.find_all("tr"):
            if saved_reports_num >= max_reports_num:
                break

            columns = row.find_all("td")

            # Skip if it's an empty row or header
            if not columns or len(columns) < 6:
                continue

            report_url_elem = columns[1].find("a")
            report_detail_page_url = (
                "https://finance.naver.com/research/" + report_url_elem["href"]
                if report_url_elem
                else None
            )

            report_title = report_url_elem.text if report_url_elem else None
            if report_title is None:
                print(f"Unexpected page form around report title")
                print(f"URL was {url}")
                print(f"Skipping this report")
                continue

            analyst_company = columns[2].text.strip()
            if analyst_company is None:
                print(f"Unexpected page form around analyst company")
                print(f"URL was {url}")
                print(f"Skipping this report")
                continue

            file_url_elem = columns[3].find("a")
            report_url = file_url_elem["href"] if file_url_elem else None
            if report_url is None:
                print(f"Unexpected page form around report url")
                print(f"URL was {url}")
                print(f"Skipping this report")
                continue

            publish_date_text = columns[4].text.strip()
            if len(publish_date_text) == 0:
                print(f"Unexpected page form around report publish date")
                print(f"URL was {url}")
                print(f"Skipping this report")
                continue
            publish_date = text_to_date(publish_date_text)

            # check if report already in DB: report with same title and publish date is considered same report
            if Report.objects.filter(
                title=report_title, publish_date=publish_date
            ).exists():
                print(f"Skipping existing report with title {report_title}")
                continue

            analysis = analyze_pdf(report_url)
            negative_points = analysis["negative points"]
            analyst_names = analysis["writers"]

            report_detail = get_report_detail_info(report_detail_page_url)
            if report_detail is None:
                print("Unexpected page form in report details")
                print(f"URL was {report_detail_page_url}")
                print(f"Skipping this report")
                continue

            target_price, written_sentiment = report_detail
            target_price = Decimal(target_price)

            # report object with missing hidden_sentiment, is_newest, next_publish_date
            price_on_publish = get_price_on_publish(stock, publish_date)
            if price_on_publish is None:
                print(f"Failed to get price on publish of report {report_title}")
                print(f"Skipping this report")
                continue
            report = Report(
                title=report_title,
                stock=stock,
                url=report_url,
                target_price=target_price,
                publish_date=publish_date,
                written_sentiment=written_sentiment,
                price_on_publish=price_on_publish,
            )

            # save analaysts to DB
            try:
                analyst_list = []
                for name in analyst_names:
                    analyst, _ = Analyst.objects.get_or_create(
                        name=name, company=analyst_company
                    )
                    analyst_list.append(analyst)
            except Exception as e:
                print(f"Exception on saving analysts: {analyst}")
                print(e)
                print(f"Skipping this report")
                continue

            hidden_sentiment = get_hidden_sentiment(
                report=report, analysts=analyst_list
            )
            next_publish_date = get_next_publish_date(
                report=report, analysts=analyst_list
            )

            report.hidden_sentiment = hidden_sentiment
            report.is_newest = next_publish_date is None
            report.next_publish_date = next_publish_date

            # save report to DB
            try:
                report.save()
                saved_reports_num += 1
            except Exception as e:
                print(f"Exception on saving report: {report}")
                print(e)
                print(f"IMPORTANT: analysts are saved but report is not. revise this report")
                print(f"Continuing to next report")
                continue

            # connect analaysts and report on DB
            try:
                for analyst in analyst_list:
                    Writes.objects.get_or_create(report=report, analyst=analyst)
            except Exception as e:
                print(f"Exception on saving 'Writes': {report} {analyst}")
                print(e)
                print(f"IMPORTANT: analysts and reports are saved, but 'writes' is not. revise this report")
                print(f"Continuing to next report")
                continue

            # save negative points on DB
            try:
                point_list = []
                for neg_point in negative_points:
                    point, _ = Point.objects.get_or_create(
                        content=neg_point, report=report, is_positive=False
                    )
                    point_list.append(point)
            except Exception as e:
                print(f"Exception on saving 'Point': {point}")
                print(e)
                print(f"IMPORTANT: analysts, reports, and writes are saved, but points are not. revise this report")
                print(f"Continuing to next report")
                break

            # Print results
            print(f"\nSaved: ")
            print(f"    report: {report}")
            print(f"    by analysts: {analyst_list}")
            print(f"    with points: {point_list}", end="\n\n")

        # 다음 페이지 없음을 의미
        if not soup.select_one("table.Nnavi td.pgRR"):
            break

        page_num += 1  # go to next page


def calculate_hit_rate_of_report():
    ## 계산 성공 리포트 수
    calculationSuccess = 0

    # hidden_sentiment_db, is_newest, stock_name, publish_date, next_publish_date

    # result = {"hit_rate" : 0,
    #           "days_hit" : 0,
    #           "days_missed" : 0,
    #           "days_to_first_hit" : 0,
    #           "days_to_first_miss" : 0
    #           }

    reports = Report.objects.filter(hit_rate=None).order_by("publish_date")

    ##calculated_reports = Report.objects.filter(hit_rate__gt=0)
    calculated_reports_length = Report.objects.filter(hit_rate__gt=0).count()

    ##print(f"calculated reports : {len(calculated_reports)}")
    print(f"calculated reports : {calculated_reports_length}")
    print(f"not-calculated reports : {len(reports)}")

    for index, report in enumerate(reports):
        print(f"리포트 적중률 계산 중 {index+1}/{len(reports)} \r", end="")

        ## 적중률 계산에 필요한 DB 정보
        hidden_sentiment = (
            -1 if report.hidden_sentiment == "SELL" else 1
        )  ## 리포트에 숨겨진 정보
        is_newest = report.is_newest  ## 가장 최신 리포트 여부
        stock_name = report.stock.name  ## 종목 이름
        search_start_date = report.publish_date.strftime("%Y%m%d")  ## 리포트 발행 일자
        search_end_date = (
            (report.publish_date + timedelta(days=365)).strftime("%Y%m%d")
            if is_newest
            else report.next_publish_date.strftime("%Y%m%d")
        )  ## 리포트 유효기간

        # print()
        # print()
        # print(f"hidden_sentiment : {hidden_sentiment}")
        # print(f"is_newest : {is_newest}")
        # print(f"itmsNm : {stock_name}")
        # print(f"beginBasDt : {search_start_date}")
        # print(f"endBasDt : {search_end_date}")

        # continue

        stockPriceApiBaseurl = os.getenv("STOCK_PRICE_API_BASE_URL")

        # 요청 파라미터 설정
        params = {
            "serviceKey": os.getenv("STOCK_PRICE_SERVICE_KEY"),
            "numOfRows": "365",  ## 검색 일수
            "itmsNm": stock_name,  ## 종목 이름
            "beginBasDt": search_start_date,  ## 검색 시작 날짜
            "endBasDt": search_end_date,  ## 검색 종료 날짜
        }

        try:
            ## GET 요청 보내기
            response = requests.get(stockPriceApiBaseurl, params=params)

            # 응답 확인
            if response.status_code == 200:
                ## XML로 반환된 데이터의 내용 추출하기 위한 처리
                xml_data = response.content
                root = ET.fromstring(xml_data)

                # clpr(종가) 요소 추출
                basDt_elements = root.findall(".//basDt")
                clpr_elements = root.findall(".//clpr")

                ## 금융위원회 주식시세 ap는 2020년까지의 주식 데이터밖에 없으므로 이 이전은 아직은 빼놓는다.
                if len(basDt_elements) == 0:
                    continue

                ##print(basDt_elements)

                startPrice = int(clpr_elements[len(basDt_elements) - 1].text)

                ## 지금은 hidden_sentiment가 SELL인 경우를 기준으로 로직 작성
                days_hit = 0
                days_missed = 0
                days_to_first_hit = 0
                days_to_first_miss = 0

                ##print(f"startPrice : {startPrice}")

                # clpr 값 출력
                for i in range(len(basDt_elements) - 2, -1, -1):
                    basDt_element = basDt_elements[i]
                    clpr_element = clpr_elements[i]

                    basDt_element = basDt_element.text
                    clpr_value = int(clpr_element.text)

                    ## 변화값 부호 * hidden_sentiment : 양수면 hit, 음수면 miss
                    variance = (clpr_value - startPrice) * hidden_sentiment

                    ## 맞췄을 경우
                    if variance > 0:
                        ##priceStatus = "맞음!"

                        if days_hit == 0:
                            days_to_first_hit = len(basDt_elements) - 1 - i

                        days_hit += 1

                    ## 틀렸을 경우
                    else:
                        ##priceStatus = "--틀림!"

                        if days_missed == 0:
                            days_to_first_miss = len(basDt_elements) - 1 - i

                        days_missed += 1

                    ##print(f"{basDt_element}의 종가 : {clpr_value} {priceStatus}")

                # print(f"hit_rate : {days_hit / (days_hit + days_missed)}")
                # print(f"days_hit : {days_hit}")
                # print(f"days_missed : {days_missed}")
                # print(f"days_to_first_hit : {days_to_first_hit}")
                # print(f"days_to_first_miss : {days_to_first_miss}")

                hit_rate = (
                    days_hit / (days_hit + days_missed)
                    if (days_hit + days_missed)
                    else 0
                )
                report.hit_rate = hit_rate
                report.days_hit = days_hit
                report.days_missed = days_missed
                report.days_to_first_hit = days_to_first_hit
                report.days_to_first_miss = days_to_first_miss

                # save report to DB
                try:
                    report.save()
                    calculationSuccess += 1
                except Exception as e:
                    print(f"Exception on saving report: {report}")
                    print(e)
                    break

            else:
                print("요청 실패:", response.status_code)

        except Exception as e:
            print(e)

    print(f"{len(reports)} 개의 리포트 중..")
    print(f"{calculationSuccess}개의 리포트 적중률 계산 성공!")
    print(f"{len(reports) - calculationSuccess}개의 리포트 적중률 계산 실패")

def calculate_hit_rate_of_single_analyst(analyst):
    # BUG: analyst with no related report returns 1(failure)

    analyst_write_instances = Writes.objects.filter(
            analyst=analyst
        )  # analyst와 연관된 Writes 뽑기
    reports = Report.objects.filter(
        writes__in=analyst_write_instances
    )  # analyst_write_instances와 연관된 Report 뽑기

    length = len(reports)
    for r in reports:
        print(r)

    total = reports.aggregate(
        total_days_hit=Sum("days_hit"),
        total_days_missed=Sum("days_missed"),
        total_days_to_first_hit=Sum("days_to_first_hit"),
        total_days_to_first_miss=Sum("days_to_first_miss"),
    )

    days_hit_sum = total["total_days_hit"]
    days_missed_sum = total["total_days_missed"]
    days_to_first_hit_sum = total["total_days_to_first_hit"]
    days_to_first_miss_sum = total["total_days_to_first_miss"]

    print(f"days_hit_sum : {days_hit_sum}")
    print(f"days_missed_sum : {days_missed_sum}")
    print(f"days_to_first_hit_sum : {days_to_first_hit_sum}")
    print(f"days_to_first_miss_sum : {days_to_first_miss_sum}")

    print()
    print()

    analyst.hit_rate = (
        days_hit_sum / (days_hit_sum + days_missed_sum)
        if (days_hit_sum + days_missed_sum)
        else 0
    )
    analyst.avg_days_hit = days_hit_sum / length
    analyst.avg_days_missed = days_missed_sum / length
    analyst.avg_days_to_first_hit = days_to_first_hit_sum / length
    analyst.avg_days_to_first_miss = days_to_first_miss_sum / length

    # save analysts to DB
    try:
        analyst.save()
    except Exception as e:
        print(f"Exception on saving report: {analyst}")
        print(e)
        return 1

    return 0

def calculate_hit_rate_of_analyst():
    calculationSuccess = 0

    # analysts = Analyst.objects.all()
    # reports = Report.objects.all()

    analysts = set(write.analyst for write in Writes.objects.all())

    for index, analyst in enumerate(analysts):
        print(f"애널리스트 적중률 계산 중 {index+1}/{len(analysts)} \r", end="")

        if calculate_hit_rate_of_single_analyst(analyst) == 0:
            calculationSuccess += 1


    print(f"{len(analysts)}명의 애널리스트 중..")
    print(f"{calculationSuccess}명의 애널리스트 적중률 계산 성공!")
    print(f"{len(analysts) - calculationSuccess}명의 에널리스트 적중률 계산 실패")

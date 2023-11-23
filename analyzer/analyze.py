import time
from io import BytesIO
import json
import os
import re
import PyPDF2
from dotenv import load_dotenv
from openai import OpenAI
import requests


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    return client


def analyze_pdf(pdf_url, test=False):
    # get analysts from the first page
    first_page_text = read_pdf(pdf_url, from_page=1, to_page=1)
    analysts = get_analysts(first_page_text, test=test)

    # get negative points from only the first two pages (pages that mainly contains text)
    all_text = read_pdf(pdf_url, to_page=2)
    negative_points = get_negative_points(all_text, test=test)

    return {"writers": analysts, "negative points": negative_points}


def get_negative_points(text_list: list, test=False) -> list:
    client = get_openai_client()
    BASE_MESSAGE = [
        {
            "role": "system",
            "content": """
                You will be provided with a stock analysis report delimited by triple quotes and a question. 
                Your task is to answer the question using only the provided text and to cite the passage(s) of the text used to answer the question.  
                If the text does not contain the information needed to answer this question then respond with an empty list(ex. []).
                If an answer to the question is provided, it must be annotated with a citation. 
                Respond in JSON format with a single key 'response' to a list of objects, where each object has keys "answer", and "citation". 
                Use key "citation" to cite relevant passages. 
                Answer in Korean. 
            """,
        },
    ]

    ret = []
    for text in text_list:
        messages = BASE_MESSAGE + [
            {
                "role": "user",
                "content": '"""'
                + str(text)
                + '"""\n'
                + "Question: What are the risks and negative points of this company?",
            }
        ]

        if test:
            print(f"\nQ: Get negative points from: \n{str(text)}")
        try:
            response = client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            answer = response.choices[0].message.content

            result = json.loads(answer)

        except Exception as e:
            print(f"Error while getting answer from GPT: {e}")
            return []

        if isinstance(result, dict) and "response" in result:
            response = result["response"]
            new_points = []
            for r in response:  # dict with keys 'answer' and 'citation' expected
                if "citation" in r:
                    if len(r["citation"]) == 0:
                        pass
                    negative_point = str(r["citation"]).strip()
                    new_points.append(negative_point)
            ret += new_points
            if test:
                print(f"    New negative points: {new_points}")

    return ret


def get_analysts(text_list: list, test=False) -> list:
    client = get_openai_client()

    BASE_MESSAGE = [
        {
            "role": "system",
            "content": """
                Use only the provided text to find the answers. 
                Respond in JSON format with a key "authors" that has a list of names as value. 
                If you can't find the answer to the question, return `{"authors": []}`
            """,
        },
        {
            "role": "user",
            "content": """
                Read the following stock analysis report and find out the author of the report. 
                If there are multiple, find all of them. 
                Return only the person's name without the position in the company. 
            """,
        },
    ]

    ret = []
    for text in text_list:
        messages = BASE_MESSAGE + [{"role": "user", "content": str(text)}]

        if test:
            print(f"\nQ: Get analysts from: \n{str(text)}")

        try:
            response = client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            answer = response.choices[0].message.content
            result = json.loads(answer)
        except Exception as e:
            print(f"Error while getting answer from GPT: {e}")
            return []

        if isinstance(result, dict) and "authors" in result:
            new_analysts = [str(e).strip() for e in result["authors"]]
            ret += new_analysts
            if test:
                print(f"    New analysts: {new_analysts}")

    return ret


def preprocessing(page_text):
    cleaned_text = re.sub(r"[\n\t]", " ", page_text)
    return cleaned_text


def read_pdf(pdf_url, from_page=1, to_page=-1, max_text_length=1800) -> list:
    pdf_response = requests.get(pdf_url)
    if pdf_response.status_code != 200:
        print(f"PDF download failed. Status code: {pdf_response.status_code}")
        return []

    try:
        pdf_data = BytesIO(pdf_response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_data)

        text_list = []
        temp = ""

        num_pages = len(pdf_reader.pages)
        if from_page <= 0:
            from_page = 1
        if to_page < 0 or to_page > num_pages:
            to_page = num_pages

        for page_number in range(from_page - 1, to_page):
            page = pdf_reader.pages[page_number]
            page_text = preprocessing(page.extract_text())
            temp += page_text
            while len(temp) >= max_text_length:
                text_list.append(temp[:max_text_length])
                temp = temp[max_text_length:]
        text_list.append(temp)

        return text_list
    except Exception as e:
        print(f"Error while reading PDF: {e}")
        return []


def test_analyze_pdf(pdf_url):
    start_time = time.time()

    print(f"analzye_pdf({pdf_url}) is called...")
    result = analyze_pdf(pdf_url, test=True)
    print(f"\nanalzye_pdf({pdf_url}) returns:")
    print(result)

    end_time = time.time()
    print(f"Elapsed time: {end_time - start_time:.2f}s", end="\n\n")


if __name__ == "__main__":
    pdf_urls = [
        # 삼성전자 리포트
        "https://ssl.pstatic.net/imgstock/upload/research/company/1699846357166.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699234215528.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1698805833360.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1698803821224.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1698879199721.pdf",
        # 카카오 리포트
        "https://ssl.pstatic.net/imgstock/upload/research/company/1699836094681.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699582274643.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699580197719.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699579099836.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699576457107.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699576266087.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699574035557.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699572383217.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1699320065563.pdf",
        # "https://ssl.pstatic.net/imgstock/upload/research/company/1698277161864.pdf",
    ]

    start_time = time.time()
    for pdf_url in pdf_urls:
        test_analyze_pdf(pdf_url)

    end_time = time.time()
    print(f"Total elapsed time: {end_time - start_time:.2f}s", end="\n\n")

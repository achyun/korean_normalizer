# coding: utf-8
# v2 : 기수,서수 버그 수정, 일월 처리 수정
# v2.1 : v2 + 슬래시
# 20220804 기수 단위에 자리, 건 추가

import re
import os
import ast
import json
from jamo import hangul_to_jamo, h2j, j2h

from ko_dictionary import english_dictionary, etc_dictionary
import pdb

PAD = '_'
EOS = '~'
PUNC = '!\'(),-.:;?'
SPACE = ' '
#20200514 슬래시 추가
SLASH = '/'

JAMO_LEADS = "".join([chr(_) for _ in range(0x1100, 0x1113)])
JAMO_VOWELS = "".join([chr(_) for _ in range(0x1161, 0x1176)])
JAMO_TAILS = "".join([chr(_) for _ in range(0x11A8, 0x11C3)])

VALID_CHARS = JAMO_LEADS + JAMO_VOWELS + JAMO_TAILS + PUNC + SPACE + SLASH
ALL_SYMBOLS = PAD + EOS + VALID_CHARS

char_to_id = {c: i for i, c in enumerate(ALL_SYMBOLS)}
id_to_char = {i: c for i, c in enumerate(ALL_SYMBOLS)}

## -------------------------------------------------------------------------
## CHECKER 
## -------------------------------------------------------------------------
quote_checker = """([`"'＂“‘])(.+?)([`"'＂”’])"""
# number_checker = "([+-]?\d[\d,]*)[\.]?\d* *"
number_checker = "([+-]?\d[\d,]*)[\.]?\d* *"
# 기수 단위의 글자를 포함하고 있어 서수임에도 기수처럼 읽는 것을 방지하기 위해
# 오류난 exception 아님
exception_checker = "(개월)"
# cardinal = 기수 = 세는 수 
cardinal_checker = "(시|명|가지|살|마리|포기|송이|수|톨|통|개|벌|척|채|다발|그루|자루|줄|켤레|그릇|잔|마디|상자|사람|곡|병|판|자리|건)"
dash_checker = number_checker + "-" + number_checker
phone_checker = "\d{3,4}-\d{4}"
## -------------------------------------------------------------------------

## -------------------------------------------------------------------------
## DICTIONARY
## -------------------------------------------------------------------------
cardinal_to_kor1 = [""] + ["한","두","세","네","다섯","여섯","일곱","여덟","아홉"]
num_to_kor = {
        '0': '영',
        '1': '일',
        '2': '이',
        '3': '삼',
        '4': '사',
        '5': '오',
        '6': '육',
        '7': '칠',
        '8': '팔',
        '9': '구',
}
num_to_kor1 = [""] + list("일이삼사오육칠팔구")
num_to_kor2 = [""] + list("만억조경해")
num_to_kor3 = [""] + list("십백천")
unit_to_kor1 = {
        '%': "퍼센트",
        'cm': "센치미터",
        'mm': "밀리미터",
        'km': "킬로미터",
        'kg': "킬로그램",
        'mg': "밀리그램"
}
unit_to_kor2 = {
        'm': "미터",
        'g': "그램"
}
upper_to_kor = {
        'A': '에이',
        'B': '비',
        'C': '씨',
        'D': '디',
        'E': '이',
        'F': '에프',
        'G': '지',
        'H': '에이치',
        'I': '아이',
        'J': '제이',
        'K': '케이',
        'L': '엘',
        'M': '엠',
        'N': '엔',
        'O': '오',
        'P': '피',
        'Q': '큐',
        'R': '알',
        'S': '에스',
        'T': '티',
        'U': '유',
        'V': '브이',
        'W': '더블유',
        'X': '엑스',
        'Y': '와이',
        'Z': '지',
}
cardinal_tenth_dict = {
        "십": "열",
        "두십": "스물",
        "세십": "서른",
        "네십": "마흔",
        "다섯십": "쉰",
        "여섯십": "예순",
        "일곱십": "일흔",
        "여덟십": "여든",
        "아홉십": "아흔"
}
## -------------------------------------------------------------------------

def is_lead(char):
    return char in JAMO_LEADS

def is_vowel(char):
    return char in JAMO_VOWELS

def is_tail(char):
    return char in JAMO_TAILS

def get_mode(char):
    if is_lead(char):
        return 0
    elif is_vowel(char):
        return 1
    elif is_tail(char):
        return 2
    else:
        return -1

def _get_text_from_candidates(candidates):
    if len(candidates) == 0:
        return ""
    elif len(candidates) == 1:
        return _jamo_char_to_hcj(candidates[0])
    else:
        return j2h(**dict(zip(["lead", "vowel", "tail"], candidates)))

def jamo_to_korean(text):
    text = h2j(text)

    idx = 0
    new_text = ""
    candidates = []

    while True:
        if idx >= len(text):
            new_text += _get_text_from_candidates(candidates)
            break

        char = text[idx]
        mode = get_mode(char)

        if mode == 0:
            new_text += _get_text_from_candidates(candidates)
            candidates = [char]
        elif mode == -1:
            new_text += _get_text_from_candidates(candidates)
            new_text += char
            candidates = []
        else:
            candidates.append(char)

        idx += 1
    return new_text

def compare_sentence_with_jamo(text1, text2):
    return h2j(text1) != h2j(text)

def tokenize(text, as_id=False):
    # jamo package에 있는 hangul_to_jamo를 이용하여 한글 string을 초성/중성/종성으로 나눈다.
    text = normalize(text)
    tokens = list(hangul_to_jamo(text)) # '존경하는'  --> ['ᄌ', 'ᅩ', 'ᆫ', 'ᄀ', 'ᅧ', 'ᆼ', 'ᄒ', 'ᅡ', 'ᄂ', 'ᅳ', 'ᆫ', '~']

    if as_id:
        return [char_to_id[token] for token in tokens] + [char_to_id[EOS]]
    else:
        return [token for token in tokens] + [EOS]

def tokenizer_fn(iterator):
    return (token for x in iterator for token in tokenize(x, as_id=False))

def normalize(text):
    # 공백과 \n 삭제
    text = text.strip()

    # 괄호 안에 있는 \d일 삭제
    # ex. '오늘(20일)' -> '오늘'
    text = re.sub('\(\d+일\)', '', text)

    # 20200514 슬래시 추가
    text = normalize_slash(text)
    # 딕셔너리 변환 ko_dictionary.py -> etc_dictionary
    text = normalize_with_dictionary(text, etc_dictionary)
    # 영어 변환 ko_dictionary.py -> english_dictionary
    text = normalize_english(text)
    # 단일 대문자는 알파벳대로 읽어준다 ex. A -> 에이
    text = re.sub('[a-zA-Z]+', normalize_upper, text)
    # 따옴표 제거
    text = normalize_quote(text)
    #숫자 변환
    text = normalize_number(text)

    return text

#20200514 슬래시 추가
def normalize_slash(text):
    #1/2 인 경우 이 분의 일 로 나오도록 앞뒤를 치환
    text = re.sub(number_checker+'/'+number_checker,r'\2 분의 \1',text)
    #더블슬래시
    text = re.sub('/{2}','/',text)
    
    return text

def normalize_with_dictionary(text, dic):
    if any(key in text for key in dic.keys()):
        pattern = re.compile('|'.join(re.escape(key) for key in dic.keys()))
        return pattern.sub(lambda x: dic[x.group()], text)
    else:
        return text

def normalize_english(text):
    def fn(m):
        word = m.group()
        if word in english_dictionary:
            return english_dictionary.get(word)
        else:
            return word

    text = re.sub("([A-Za-z]+)", fn, text)
    return text

def normalize_upper(text):
    text = text.group(0)

    if all([char.isupper() for char in text]):
        return "".join(upper_to_kor[char] for char in text)
    else:
        return text

def normalize_quote(text):
    def fn(found_text):
        found_text = found_text.group()
        unquoted_text = found_text[1:-1]
        return unquoted_text

    return re.sub(quote_checker, fn, text)

def normalize_number(text):
    # 단위 변환
    text = normalize_with_dictionary(text, unit_to_kor1)
    text = normalize_with_dictionary(text, unit_to_kor2)

    # 전화번호 변환
    text = re.sub(phone_checker, lambda x : phone_to_korean(x), text)

    # 숫자-숫자 -> 숫자 다시 숫자
    text = re.sub(dash_checker, lambda x : dash_to_korean(x), text)

    # 기수 단위의 글자를 포함하고 있어 서수임에도 기수처럼 읽히는 예외 단위 처리 
    # ex.) 개월
    text = re.sub(number_checker + exception_checker,
            lambda x: number_to_korean(x, False, True), text)

    # 기수
    text = re.sub(number_checker + cardinal_checker,
            lambda x: number_to_korean(x, True), text)

    # 서수
    text = re.sub(number_checker,
            lambda x: number_to_korean(x, False), text)
    return text

def dash_to_korean(num_str):
    return num_str.group().replace('-',' 다시 ')

def phone_to_korean(num_str):
    kor = ""
    num_str = num_str.group().replace('-',' ')
    kor += re.sub('\d', lambda x: num_to_kor[x.group()], num_str)

    return kor


def number_to_korean(num_str, is_cardinal=False, is_exception=False):
    post_space = 0
    # 숫자와 단위 분리
    if is_cardinal:
        num_str, unit_str = num_str.group(1), num_str.group(2)
    else:
        if is_exception :
            num_str, unit_str = num_str.group(1), num_str.group(2)
        else :
            num_str, unit_str = num_str.group(), ""
    
    for i in reversed(range(len(num_str))) :
        if num_str[i] == ' ' :
            post_space += 1
        else :
            break

    #쉼표 제거 -> 100,000같은거 
    num_str = num_str.replace(',', '')

    #소수점 분리
    check_float = num_str.split('.')
    if len(check_float) == 2:
        digit_str, float_str = check_float
    elif len(check_float) >= 3:
        raise Exception(" [!] Wrong number format")
    else:
        digit_str, float_str = check_float[0], None

    if is_cardinal and float_str is not None:
        raise Exception(" [!] `is_cardinal` and float number does not fit each other")

    digit = int(digit_str)

    if digit_str.startswith("-"):
        digit, digit_str = abs(digit), str(abs(digit))

    # 자릿수별로 숫자를 한글로 변환
    kor = ""
    kor_under_10000 = ""
    size = len(str(digit))
    tmp = []
    digit_str = digit_str.strip()
    zero_count = 0
    for i, v in enumerate(digit_str, start=1):
        v = int(v)
        if v != 0:
            # 숫자
            # 1110 -> 일천일백일십 처럼 읽으면 안되므로 v가 1일 땐 숫자는 버린다.
            # 하지만 1210000 -> 백이십일만 처럼 만억조경해 단위에서는 '일'도 표시해 줘야 한다.
            if v != 1 or (size - i) % 4 == 0 :
                if is_cardinal and (size - i) < 2:
                    # 기수(세는 수)이고 자리수가 100의 자리 미만일 때
                    # 3,333개와 같은 기수도 100의 자리 이상은 삼만삼천삼백 과 같이 서수처럼 읽고, 서른 세 개와 같이 100의 자리 미만은 기수로 읽는다.
                    tmp += cardinal_to_kor1[v]
                elif is_cardinal and (size - i) >= 2:
                    # 기수(세는 수)이고 자리수가 100의 자리 이상일 때
                    tmp += num_to_kor1[v]
                else:
                    # 서수일 때
                    tmp += num_to_kor1[v]

            # 단위(십, 백, 천)
            tmp += num_to_kor3[(size - i) % 4]
        else :
            #v = 0일 때. -> 개선 필요
            #이월 일일 영시 같은 케이스 커버
            if len(digit_str) == 1 : 
                tmp += "공"
            else :
                #00시 로직. 
                #i가 len(digit_str) 보다 작을 때 -> 처음 나오는 0이 아닐 때
                if i < len(digit_str) : 
                    zero_count += 1
                elif i == len(digit_str) and zero_count == len(digit_str)-1 : # i가 len(digit_str)이랑 같고(마지막 0일 때), 이전 숫자가 0일 때
                    zero_count += 1
                    for i in range(zero_count) :
                        tmp += "공"
                    zero_count = 0    

        if (size - i) % 4 == 0 and len(tmp) != 0:
            # 4 자리마다 만, 억, 조, 경, 해 붙이기
            if (size-i) < 4 : # 10,000 이전 숫자와 10,000 이후 숫자를 분기
                kor_under_10000 += "".join(tmp)
                tmp = []
                kor += num_to_kor2[int((size - i) / 4)]
            else :
                kor += "".join(tmp)
                tmp = []
                kor += num_to_kor2[int((size - i) / 4)]
        
        if size == 5 and i == 1 :
            # 일만으로 시작하는 현상 fix
            kor = kor.replace('일', '')

    if is_cardinal :
        # 두십 -> 스물과 같이 10의자리에 있는 기수 변경해준다.
        if any(word in kor_under_10000 for word in cardinal_tenth_dict):
            kor_under_10000 = re.sub(
                    '|'.join(cardinal_tenth_dict.keys()),
                    lambda x: cardinal_tenth_dict[x.group()], kor_under_10000)
    
    kor += kor_under_10000

    # 소수점 이하 자리가 있을 때
    if float_str is not None:
        kor += "쩜 "
        kor += re.sub('\d', lambda x: num_to_kor[x.group()], float_str)

    # 숫자가 +또는 -로 시작하는 경우
    if num_str.startswith("+"):
        kor = "플러스 " + kor
    elif num_str.startswith("-"):
        kor = "마이너스 " + kor
    
    space = ''
    for i in range(post_space):
        space += ' '

    return kor + space + unit_str

if __name__ == "__main__":
    def test_normalize(text):
        print("="*30)
        print(text)
        print(normalize(text))
        print("="*30)
    test_normalize("60 대 30으로")
    test_normalize("2020년 월드컵에서는 한국이 4강")
    test_normalize("3개월 전에 골프를 치다가")
    test_normalize("1025호실 환자")
    test_normalize("2013년에는 작은 아파트에 대한")
    test_normalize("국어 시험에서 80점을 받았어요.")
    test_normalize('근처에 24시간 여는 슈퍼마켓 있나요?')
    test_normalize('지금은 23시10분 입니다')
    test_normalize('아버지는 20살 때부터 버스를 모셨다.')
    test_normalize("이 상자는 가로 30, 세로 50, 높이 20센티다.")
    test_normalize("3, 6, 9 게임 아세요?")
    test_normalize("남은 시간이 6개월이래요")
    test_normalize("36개월 할부")
    test_normalize("114에 전화를 해서 번호를 알아보시지 그러세요?")
    test_normalize("축구에서 한 팀은 11명으로 이루어진다.")
    test_normalize("그 연극은 5월 1일부터 10월 31일까지 월요일을 제외하고 매일 공연됩니다.")
    test_normalize("우리의 목표는 에너지 소비를 10% 줄이는 것입니다.")
    test_normalize('5 시 36분 32초')
    test_normalize('2 명 입니다')
    test_normalize('3명 입니다')
    test_normalize("mp3 파일을 홈페이지에서 다운로드 받으시기 바랍니다.")
    test_normalize("오늘(13일) 3,600마리 강아지가")
    test_normalize("60.3%")
    test_normalize("2월 1일 00시")
    test_normalize("123,455,123개")
    test_normalize("더블 슬래시 테스트 : // ")
    test_normalize("슬래시 테스트 : 1/2, 테/스/트, 3234/1234.")
    test_normalize("AS")
    test_normalize("33,333개")
    test_normalize("0")
    test_normalize("00")
    test_normalize("000")
    test_normalize("03")
    test_normalize("세종특별자치시 한누리대로 1843-10")
    test_normalize("제 전화번호는 010-1234-5678이에요.")
    test_normalize("13시")
    test_normalize("010-1234-5678")
    test_normalize("1588-9898")
    #print(list(hangul_to_jamo(list(hangul_to_jamo('남은 시간이 "6개월이래요”')))))

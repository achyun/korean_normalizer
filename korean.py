# coding: utf-8
# v2 : 기수,서수 버그 수정,    일월 처리 수정

import re
import os
import ast
import json
from jamo import hangul_to_jamo, h2j, j2h

from ko_dictionary import english_dictionary, etc_dictionary

PAD = '_'
EOS = '~'
PUNC = '!\'(),-.:;?'
SPACE = ' '

JAMO_LEADS = "".join([chr(_) for _ in range(0x1100, 0x1113)])
JAMO_VOWELS = "".join([chr(_) for _ in range(0x1161, 0x1176)])
JAMO_TAILS = "".join([chr(_) for _ in range(0x11A8, 0x11C3)])

VALID_CHARS = JAMO_LEADS + JAMO_VOWELS + JAMO_TAILS + PUNC + SPACE
ALL_SYMBOLS = PAD + EOS + VALID_CHARS

char_to_id = {c: i for i, c in enumerate(ALL_SYMBOLS)}
id_to_char = {i: c for i, c in enumerate(ALL_SYMBOLS)}

quote_checker = """([`"'＂“‘])(.+?)([`"'＂”’])"""
number_checker = "([+-]?\d[\d,]*)[\.]?\d* *"
count_checker = "(시|명|가지|살|마리|포기|송이|수|톨|통|개|벌|척|채|다발|그루|자루|줄|켤레|그릇|잔|마디|상자|사람|곡|병|판)"

#count_to_kor1 = [""] + ["하나","둘","셋","넷","다섯","여섯","일곱","여덟","아홉"]
count_to_kor1 = [""] + ["한","두","세","네","다섯","여섯","일곱","여덟","아홉"]

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
        #단위이므로 하나 띄어준다~
        '%': "퍼센트",
        'cm': "센치미터",
        'mm': "밀리미터",
        'km': "킬로미터",
        'kg': "킬로그램",
        # 'g':  '그램'  # num+g 으로 만들어야됨
}
unit_to_kor2 = {
        'm': "미터",
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

count_tenth_dict = {
        "십": "열",
        "두십": "스물",
        "세십": "서른",
        "네십": "마흔",
        "다섯십": "쉰",
        "여섯십": "예순",
        "일곱십": "일흔",
        "여덟십": "여든",
        "아홉십": "아흔",
        "두백":"이백",
        "세백":"삼백",
        "네백":"사백",
        "다섯백":"오백",
        "여섯백":"육백",
        "일곱백":"칠백",
        "여덟백":"팔백",
        "아홉백":"구백",
        "두천":"이천",
        "세천":"삼천",
        "네천":"사천",
        "다섯천":"오천",
        "여섯천":"육천",
        "일곱천":"칠천",
        "여덟천":"팔천",
        "아홉천":"구천",
        "두만":"이만",
        "세만":"삼만",
        "네만":"사만",
        "다섯만":"오만",
        "여섯만":"육만",
        "일곱만":"칠만",
        "여덟만":"팔만",
        "아홉만":"구만",
        "두억":"이억",
        "세억":"삼억",
        "네억":"사억",
        "다섯억":"오억",
        "여섯억":"육억",
        "일곱억":"칠억",
        "여덟억":"팔억",
        "아홉억":"구억",
        "두십억":"이십억"

}

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

    # 괄호 안에 있는 \d일 삭제 ex. '(20일)' -> ''
    text = re.sub('\(\d+일\)', '', text)
    # 무슨 역할인지...
    text = re.sub('\([⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]+\)', '', text)

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
        from nltk import sent_tokenize # NLTK doesn't along with multiprocessing

        found_text = found_text.group()
        unquoted_text = found_text[1:-1]

        sentences = sent_tokenize(unquoted_text)
        return " ".join(["'{}'".format(sent) for sent in sentences])

    return re.sub(quote_checker, fn, text)

def normalize_number(text):
    # 단위 변환
    text = normalize_with_dictionary(text, unit_to_kor1)
    text = normalize_with_dictionary(text, unit_to_kor2)
    # text = re.sub('(\d+),(\d+)',r'\1\2',text)   # 3,600 마리 강아지
    # print(text)
    
    # 개월 변환
    text = re.sub("([+-]?\d[\d,]*)[\.]?\d* *개월",lambda x: number_to_korean(x, False), text)
    # print('re first ',text)

    #서수
    text = re.sub(number_checker + count_checker,
            lambda x: number_to_korean(x, True), text)

    #기수
    text = re.sub(number_checker,
            lambda x: number_to_korean(x, False), text)
    return text

def number_to_korean(num_str, is_count=False):
    #기수/서수
    if is_count:
        num_str, unit_str = num_str.group(1), '' + num_str.group(2)
    else:
        num_str, unit_str = num_str.group(), ""
    #개월
    if '개월' in num_str:
        num_str = num_str.replace('개월','')
        unit_str = '개월'
    #쉼표 제거 -> 100,000같은거
    num_str = num_str.replace(',', '')
    num = ast.literal_eval(num_str)

    #if num == 0:
    #    kor = "영"

    #소수점 분리
    check_float = num_str.split('.')
    if len(check_float) == 2:
        digit_str, float_str = check_float
    elif len(check_float) >= 3:
        raise Exception(" [!] Wrong number format")
    else:
        digit_str, float_str = check_float[0], None

    if is_count and float_str is not None:
        raise Exception(" [!] `is_count` and float number does not fit each other")

    digit = int(digit_str)

    if digit_str.startswith("-"):
        digit, digit_str = abs(digit), str(abs(digit))

    #자릿수별로 변환
    kor = ""
    kor_under_10000 = ""
    size = len(str(digit))
    tmp = []
    digit_str = digit_str.strip()
    zero_count = 0
    #print('digit : {}'.format(digit))
    print('digit_str : {}'.format(digit_str))
    for i, v in enumerate(digit_str, start=1):
        v = int(v)

        if v != 0:
            #일천일백일십 방지
            if v != 1 or (size - i) % 4 == 0 :
                if is_count and (size - i) < 4:
                    tmp += count_to_kor1[v]
                elif is_count and (size - i) >= 4: #수가 커지면 서른삼만천백열한개 이런식으로 돼서 분기
                    tmp += num_to_kor1[v]
                else:
                    tmp += num_to_kor1[v]

            tmp += num_to_kor3[(size - i) % 4]
            #print('i : {}'.format(i))
            #print('v : {}'.format(v))
            #print('tmp : {}'.format(tmp))
        else :
            #v = 0일 때.
            #이월 일일 영시 같은 케이스 커버
            if len(digit_str) == 1 : 
                tmp += "영"
            else :
                #00시 로직. 
                #i가 len(digit_str) 보다 작을 때 -> 처음 나오는 0이 아닐 때
                if i < len(digit_str) : 
                    zero_count += 1
                elif i == len(digit_str) and zero_count == len(digit_str)-1 : # i가 len(digit_str)이랑 같고(마지막 0일 때), 이전 숫자가 0일 때
                    zero_count += 1
                    for i in range(zero_count) :
                        tmp += "영"
                    zero_count = 0    


        if (size - i) % 4 == 0 and len(tmp) != 0:
             
            if (size-i) < 4 : # 10,000 이전 숫자와 10,000 이후 숫자를 분기
                kor_under_10000 += "".join(tmp)
                tmp = []
                kor += num_to_kor2[int((size - i) / 4)]
            else :
                kor += "".join(tmp)
                tmp = []
                kor += num_to_kor2[int((size - i) / 4)]
            #print('kor : {}{}'.format(kor,kor_under_10000))

    if is_count:
        if kor.startswith("한") and len(kor) > 1:
            kor = kor[1:]
        # 10000 이전 숫자도 동일로직
        if kor_under_10000.startswith("한") and len(kor_under_10000) > 1:
            kor_under_10000 = kor_under_10000[1:]

        # 열 스물 서른 > 10,000 이전까지만 적용
        if any(word in kor_under_10000 for word in count_tenth_dict):
            kor_under_10000 = re.sub(
                    '|'.join(count_tenth_dict.keys()),
                    lambda x: count_tenth_dict[x.group()], kor_under_10000)
        # 더해준다!
    kor = kor + kor_under_10000

    if not is_count and kor.startswith("일") and len(kor) > 1:
        kor = kor[1:]

    if float_str is not None:
        kor += "쩜 "
        kor += re.sub('\d', lambda x: num_to_kor[x.group()], float_str)

    if num_str.startswith("+"):
        kor = "플러스 " + kor
    elif num_str.startswith("-"):
        kor = "마이너스 " + kor

    return kor + unit_str

if __name__ == "__main__":
    def test_normalize(text):
        print("="*30)
        print(text)
        print(normalize(text))
        print("="*30)
    test_normalize("제 전화번호는 01012345678이에요.")
    test_normalize("60 대 30으로")
    test_normalize("2020년 월드컵에서는 한국74이 4강")
    test_normalize("3개월 전에 골프를 치다가")
    test_normalize("1025호실 환자")
    test_normalize("2013년에는 작은 아파트에 대한")
    test_normalize("국어 시험에서 80점을 받았어요.")
    test_normalize('근처에 24시간 여는 슈퍼마켓 있나요?')
    test_normalize('지금은 23시10분 입니다')
    test_normalize('아버지는 20살 때부터 버스를 모셨다.')
    #test_normalize("""아버지는 '20살' 때부터 버스를 모셨다.""")
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
    test_normalize("33001명의 사람이 모였습니다")
    test_normalize("60.3%")
    test_normalize("3333313333113111개")
    test_normalize("3333313333113111")
    test_normalize("33333133331131110")
    test_normalize("2월 1일 00시")
    test_normalize("0")
    test_normalize("0시")

    #print(list(hangul_to_jamo(list(hangul_to_jamo('남은 시간이 "6개월이래요”')))))
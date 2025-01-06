import re

def extract_numbers(input_string):
    numbers = re.findall(r'\d+', input_string)

    numbers = [int(num) for num in numbers]
    return numbers


def extract_episode(input_string,index):
    numbers = re.findall(r'\d+', input_string)
    numbers = [int(num) for num in numbers]
    return numbers[0] if numbers else index


def extract_id(input_id):
    result = input_id.split("eneyida_")[1]
    return  result

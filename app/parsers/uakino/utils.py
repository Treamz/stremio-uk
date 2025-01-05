import re
from bs4 import BeautifulSoup


def extract_numbers(input_string):
    numbers = re.findall(r'\d+', input_string)

    numbers = [int(num) for num in numbers]
    return numbers


def parse_true_id(input_id: str) -> str:
    # Split the string on the first hyphen
    return input_id.split('-')[0]


def parse_first_number_from_data_id(tag) -> int:
    """
    Extract the first number from the `data-id` attribute of an HTML element.
    """
    if tag and "data-id" in tag.attrs:
        data_id = tag["data-id"]

        # Extract the first number using a regular expression
        match = re.match(r'(\d+)', data_id)
        if match:
            return int(match.group(1))  # Return the first number as an integer
        else:
            raise ValueError(f"No number found in data-id: {data_id}")
    else:
        raise ValueError("data-id not found in the provided tag.")
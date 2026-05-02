import csv
import json
from datetime import date, datetime
from pathlib import Path

# Constants
DEPARTMENTS_AND_BINS = {
    "MDR": {"GR", "BL", "AX"},
    "SA": {"SP", "BL"},
    "WB": {"GR", "AX"},
}
AUTHORIZED_PROCESSORS = {
    "James.L",
    "Nora.K",
    "Arthur.B",
    "Lena.P",
    "Felix.G",
    "Dr.Voss",
    "Clara.M",
}
CATEGORIES = ("alpha", "beta", "gamma", "delta")
START_DATE = date(2025, 10, 1)
END_DATE = date(2025, 12, 31)
NORA_END_DATE = date(2025, 11, 15)
MDR_CSV_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
TXT_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def convert_raw_timestamp(value, fmt):
    try:
        converted_value = datetime.strptime(value, fmt).date()
    except (ValueError, TypeError):
        return None
    else:
        return converted_value


def make_basic_validations(department, processor, timestamp):
    """
    Make the first level validations (rules 1, 2, 6, 7 and 12)
    """
    correct_department = department in DEPARTMENTS_AND_BINS
    processor_authorized = processor in AUTHORIZED_PROCESSORS
    correct_date = timestamp >= START_DATE and timestamp <= END_DATE
    is_weekday = timestamp.isoweekday() not in [6, 7]
    if processor == "Nora.K" and timestamp > NORA_END_DATE:
        processor_authorized = False

    return all([correct_department, processor_authorized, correct_date, is_weekday])


def make_entry_verifications(department, bin_code, value, category):
    """
    Make second level validation (rules 3, 4, 5, 8, 9, 10)
    """
    correct_bin = bin_code in DEPARTMENTS_AND_BINS.get(department, set())
    valid_value = value > 0 and value < 1000
    valid_category = category in CATEGORIES

    return all([correct_bin, valid_value, valid_category])


def verify_duplicates(raw_data, session_id, timestamp):
    """
    Verify if session_id already exists send flag for substitution (rule 11)
    """
    has_to_replace = False
    session_data = raw_data.get(session_id)
    attached_timestamp = session_data.get("timestamp")
    if attached_timestamp > timestamp:
        has_to_replace = True
    return has_to_replace


def read_and_process_csv(file, raw_data):
    with open(file, "rt") as csv_file:
        csv_reader = list(csv.DictReader(csv_file))

        session_id = csv_reader[0].get("session_id")
        department = csv_reader[0].get("department")
        processor = csv_reader[0].get("processor")
        raw_timestamp = csv_reader[0].get("timestamp")
        timestamp = convert_raw_timestamp(raw_timestamp, MDR_CSV_TIMESTAMP_FORMAT)
        if timestamp is None:
            return
        is_valid_basic = make_basic_validations(department, processor, timestamp)
        if not is_valid_basic:
            return

        if session_id in raw_data:
            has_to_replace = verify_duplicates(raw_data, session_id, timestamp)
            if not has_to_replace:
                return

        raw_data[session_id] = {"timestamp": timestamp, "value": 0}

        for entry in csv_reader:
            bin_code = entry.get("bin")
            try:
                value = float(entry.get("output_metric", 0))
            except ValueError:
                value = 0
            category = entry.get("classification")
            is_valid_entry = make_entry_verifications(
                department, bin_code, value, category
            )
            if not is_valid_entry:
                continue
            raw_data[session_id]["value"] += value


def read_and_process_txt(file, raw_data):
    with open(file, "rt") as txt_file:
        split_info = txt_file.read().splitlines()

        session_id = split_info[0].split(":")[-1].strip()
        processor = split_info[1].split(":")[-1].strip()
        department = split_info[2].split(":")[-1].strip()
        raw_timestamp = split_info[3].split(": ")[-1].strip()
        timestamp = convert_raw_timestamp(raw_timestamp, TXT_TIMESTAMP_FORMAT)
        if timestamp is None:
            return
        is_valid_basic = make_basic_validations(department, processor, timestamp)

        if not is_valid_basic:
            return
        if session_id in raw_data:
            has_to_replace = verify_duplicates(raw_data, session_id, timestamp)
            if not has_to_replace:
                return

        raw_data[session_id] = {"timestamp": timestamp, "value": 0}

        entries = split_info[5:]

        for entry in entries:
            split_entry = entry.split("|")
            if len(split_entry) < 4:
                continue
            bin_code = split_entry[1].split(":")[-1].strip()
            try:
                value = float(split_entry[2].split(":")[-1].strip())
            except ValueError:
                value = 0
            category = split_entry[3].split(":")[-1].strip()
            is_valid_entry = make_entry_verifications(
                department, bin_code, value, category
            )
            if not is_valid_entry:
                continue
            raw_data[session_id]["value"] += value


def read_and_process_mdr(file, raw_data):
    with open(file, "rt") as json_file:
        try:
            content = json.load(json_file)
        except json.JSONDecodeError:
            return
        else:
            session_id = content.get("session_id")
            department = content.get("department")
            processor = content.get("processor")
            raw_timestamp = content.get("timestamp")
            timestamp = convert_raw_timestamp(raw_timestamp, MDR_CSV_TIMESTAMP_FORMAT)
            if timestamp is None:
                return
            is_valid_basic = make_basic_validations(department, processor, timestamp)

            if not is_valid_basic:
                return

            if session_id in raw_data:
                has_to_replace = verify_duplicates(raw_data, session_id, timestamp)
                if not has_to_replace:
                    return

            raw_data[session_id] = {"timestamp": timestamp, "value": 0}

            entries = content.get("entries", [])

            for entry in entries:
                bin_code = entry.get("bin")
                try:
                    value = float(entry.get("value", 0))
                except ValueError:
                    value = 0
                category = entry.get("category")
                is_valid_entry = make_entry_verifications(
                    department, bin_code, value, category
                )
                if not is_valid_entry:
                    continue
                raw_data[session_id]["value"] += value


def process_data_refinement():
    """
    Divide data by file extension and calls the appropriate function for each
    """

    raw_data = {}
    for root, _, files in Path("./sessions").walk():
        for file in files:
            file_path = f"{root}/{file}"
            if file.endswith(".mdr"):
                read_and_process_mdr(file_path, raw_data)
            elif file.endswith(".csv"):
                read_and_process_csv(file_path, raw_data)
            elif file.endswith(".txt"):
                read_and_process_txt(file_path, raw_data)
            else:
                continue
    return raw_data


def sum_data_refinement(data):
    return sum(item["value"] for item in data.values())


if __name__ == "__main__":
    refined_data = process_data_refinement()
    sum_value = sum_data_refinement(refined_data)
    print(sum_value)

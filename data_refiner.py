import json
from pathlib import Path
from datetime import datetime, date

# Constants
DEPARTMENTS_AND_BINS = {
    "MDR": ["GR", "BL", "AX"],
    "SA": ["SP", "BL"],
    "WB": ["GR", "AX"],
}
AUTHORIZED_PROCESSORS = (
    "James.L",
    "Nora.K",
    "Arthur.B",
    "Lena.P",
    "Felix.G",
    "Dr.Voss",
    "Clara.M",
)
CATEGORIES = ("alpha", "beta", "gamma", "delta")
START_DATE = date(2025, 10, 1)
END_DATE = date(2025, 12, 31)
NORA_END_DATE = date(2025, 11, 15)


def convert_raw_timestamp_mdr(value):
    """
    Convert string to a datetime.date value in .mdr files
    """
    try:
        converted_value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").date()
    except (ValueError, TypeError):
        return None
    else:
        return converted_value


def convert_raw_timestamp_txt(value):
    """
    Convert string to a datetime.date value in .txt files
    """
    try:
        converted_value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").date()
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


def make_entry_verifications(department, bin, value, category):
    """
    Make second level validation (rules 3, 4, 5, 8, 9, 10)
    """
    correct_bin = bin in DEPARTMENTS_AND_BINS.get(department, [])
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
    pass


def read_and_process_txt(file, raw_data):
    with open(file, "rt") as txt_file:
        splitted_info = txt_file.read().splitlines()

        session_id = splitted_info[0].split(":")[-1].strip()
        processor = splitted_info[1].split(":")[-1].strip()
        department = splitted_info[2].split(":")[-1].strip()
        raw_timestamp = splitted_info[3].split(": ")[-1].strip()
        timestamp = convert_raw_timestamp_txt(raw_timestamp)
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

        entries = splitted_info[5:]

        for entry in entries:
            splitted_entry = entry.split("|")
            if len(splitted_entry) < 4:
                continue
            bin = splitted_entry[1].split(":")[-1].strip()
            try:
                value = float(splitted_entry[2].split(":")[-1].strip())
            except ValueError:
                value = 0
            category = splitted_entry[3].split(":")[-1].strip()
            is_valid_entry = make_entry_verifications(department, bin, value, category)
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
            timestamp = convert_raw_timestamp_mdr(raw_timestamp)
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
                bin = entry.get("bin")
                try:
                    value = float(entry.get("value", 0))
                except ValueError:
                    value = 0
                category = entry.get("category")
                is_valid_entry = make_entry_verifications(
                    department, bin, value, category
                )
                if not is_valid_entry:
                    continue
                raw_data[session_id]["value"] += value


def process_data_refinement():
    """
    Divide data by file extension and calls the appropriate function for each
    """

    raw_data = {}
    for root, dirs, files in Path("./sessions").walk():
        for file in files:
            file_path = f"{root}/{file}"
            if file.endswith(".mdr"):
                read_and_process_mdr(file_path, raw_data)
            # elif file.endswith(".csv"):
            #     read_and_process_csv(file_path, raw_data)
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

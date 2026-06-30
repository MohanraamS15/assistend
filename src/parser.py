import re

PURPOSES = {
    "Promotional",
    "Transactional/Service"
}


def parse_page(lines):
    records = []

    state = "SERIAL"

    serial = ""
    header = ""
    entity_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Skip first page heading
        if line in {
            "List of Headers associated with Principal Entities Registered in DLT",
            "S.No",
            "Header",
            "Entity Name",
            "Purpose"
        }:
            continue

        # Waiting for Serial Number
        if state == "SERIAL":

            if re.fullmatch(r"\d+", line):
                serial = line
                state = "HEADER"

            continue

        # Waiting for Header
        elif state == "HEADER":

            header = line
            entity_lines = []

            state = "ENTITY"

            continue

        # Reading Entity
        elif state == "ENTITY":

            if line in PURPOSES:

                records.append({
                    "S.No": serial,
                    "Header": header,
                    "Entity Name": " ".join(entity_lines),
                    "Purpose": line
                })

                state = "SERIAL"

            else:

                entity_lines.append(line)

    return records
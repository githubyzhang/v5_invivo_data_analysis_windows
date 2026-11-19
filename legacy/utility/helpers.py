import json
import os
import re


def tuple_to_id(addr):
    """
    Convert a tuple address to an integer pid

    Args:
        addr (tuple): tuple consisting address (row, col), range from 1 to 64

    Returns:
        pid (int): integer pid, range from 0 to 4095
    """
    pid = (addr[0]-1) * 64 + (addr[1]-1)
    return pid


def id_to_string(pid):

    addr = (pid // 64 + 1, pid % 64 + 1)

    row_label = '0'+str(addr[0]) if addr[0] < 10 else str(addr[0])
    col_label = '0'+str(addr[1]) if addr[1] < 10 else str(addr[1])
    label = row_label + col_label
    return label


def save_patterns_to_json(
    patterns: dict[str, list[int]],
    path: str,
    name: str = "stimulation_pattern",
    description: str = "",
) -> None:
    data = {
        "name": name,
        "description": description,
        "patterns": patterns,
    }

    text = json.dumps(data, indent=4)

    # Collapse numeric lists like:
    # [
    #     1,
    #     2,
    #     3
    # ]
    # into: [1, 2, 3]
    def collapse_numeric_list(match):
        body = match.group(1)
        nums = re.findall(r"-?\d+", body)
        return "[" + ", ".join(nums) + "]"

    text = re.sub(
        r"\[\s*((?:-?\d+\s*,?\s*)+)\]",
        collapse_numeric_list,
        text,
        flags=re.MULTILINE,
    )

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)



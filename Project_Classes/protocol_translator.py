from pathlib import Path

# project_dictionary/ sits next to Project_Classes/ at the repo root
_DICT_DIR = Path(__file__).resolve().parent.parent / "project_dictionary"


def _read_lines(filename):
    with open(_DICT_DIR / filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _load_separators(filename="seperator_values.txt"):
    # lines look like:  SEP='###_DATA_SEPARATOR_###'
    seps = {}
    for line in _read_lines(filename):
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        seps[name.strip()] = value.strip().strip("'").strip('"').encode()
    return seps


def _load_code_flags(filename="sql_query_flags.txt"):
    # lines look like:  01 = 'username_login'
    flags = {}
    for line in _read_lines(filename):
        if "=" not in line:
            continue
        code, name = line.split("=", 1)
        name = name.strip().strip("'").strip('"')
        flags[name] = code.strip().encode()
    return flags


def _load_action_flags(filename="client_actions_flags.txt"):
    # same 'code = name' format as the SQL flags, e.g.  01 = kill  ->  {'kill': b'01'}
    return _load_code_flags(filename)


# --- Separators ---
_seps = _load_separators()
SEP = _seps["SEP"]
COLSEP = _seps["COLSEP"]
ROWSEP = _seps["ROWSEP"]

# --- Flag dictionaries ---
sql_query_flags = _load_code_flags()
client_actions = _load_action_flags()

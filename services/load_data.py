import json
from json import JSONDecodeError
from config import USERS_JSON_PATH


def write_json():
    print(1)



def load_users() -> list[dict[str, object]]:
    
    try:
        with open(USERS_JSON_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, JSONDecodeError):
        return []


def save_user(user_id: str, user_name: str):
    users_list = load_users()

    # if any(users.get('user_id') == user_id for user in users_list):
    #     return False
    
    for user in users_list:
        if user['user_id'] == user_id:
            return False
        
    users_list.append({
        "user_id" : user_id,
        "user_name" : user_name
    })

    with open(USERS_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(users_list, file, ensure_ascii=False, indent=2)

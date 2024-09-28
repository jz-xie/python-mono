
from hashlib import sha256

def mask_json(obj: dict, mask_json_tag=None):
    
    # schema = obj  # a moving reference to internal objects within obj
        # Check if mask_json_tag is None
    if mask_json_tag is None:
        obj = f'**MASKED**{sha256(str(obj).encode()).hexdigest()}'
        return obj
    # Split the keyString into an array of keys
    paths = [path.strip() for path in mask_json_tag.split(',')]
    for path in paths:
        
        current_object = obj
        key_list = path.split('.')
        
        for key in key_list[:-1]:
            
            if key not in current_object:
                raise ValueError(f"The key '{key}' does not exist in '{str(current_object.keys())}'")
            else:
                current_object = current_object[key]
                
        last_key = key_list[-1]
        
        if last_key in current_object:
            hashed_value = f'**MASKED**{sha256(str(current_object[last_key]).encode()).hexdigest()}'
            current_object[last_key] = hashed_value
        else: 
            raise ValueError(f"The key '{last_key}' does not exist in '{str(current_object.keys())}'")

# Example usage
if __name__ == "__main__":
    json_data = {
        "user": {
            "name": 2134,
            "age": 1,
            "contact": {
            "email": "john.doe@example.com",
            "address": {
                "street": 1
            }
            }
        }
        }

    output = mask_json(json_data)
    # output = mask_json(json_data)
    # output = mask_json(json_data, "user.contact.email")
    print(output)
    print(json_data)
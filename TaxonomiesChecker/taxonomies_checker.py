"""
This files takes as input a 'machinetag.json' file and verifies if it's a valid MISP taxonomy file, and also provides a feedback on how to fix it.
"""
import argparse
import json
import sys
import logging
from functools import reduce

class FreezableDict(dict):
    __frozen = False

    def freeze (self):
        self.__frozen = True

    def __setitem__ (self, key, value):
        if self.__frozen and key not in self:
            raise ValueError('Dictionary is frozen')
        super().__setitem__(key, value)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def load_json_file(file_path: str, silent: bool) -> dict:
    """Load and return data from a JSON file."""
    try:
        if not silent:
            logging.info(f"Loading JSON file: {file_path}")
        with open(file_path, encoding='utf8', mode='r') as file:
            data = json.load(file)

        if not silent:
            logging.info(f"Successfully loaded JSON file: {file_path}")
        return data

    except Exception as e:
        if not silent:
            logging.error(f"Error loading JSON file: {e}")
        
        return {}
        
 
def check_fields(present_fields: list[str], silent: bool) -> bool:
    """
    Checks which mandatory fields are missing and which fields are not allowed.
    """
    present_fields: set[str] = set(present_fields)
    mandatory_fields: set[str] = {'namespace', 'description', 'version', 'predicates'}
    correct_fields = mandatory_fields.union({'refs', 'exclusive', 'expanded', 'values'})
    result = present_fields <= correct_fields
    if not silent:
        if len(present_fields - correct_fields) > 0:
            logging.error(f"There are fields in the file that are not allowed: {present_fields - correct_fields}")

        if len(mandatory_fields - present_fields) > 0:
            logging.error(f"There are mandatory fields in the file that are missing: {mandatory_fields - present_fields}")
    
    return result
    

def is_valid_predicate(predicate: dict) -> bool:
    return set(predicate.keys()).issubset({'value', 'expanded', 'description', 'colour'}) and \
           bool(reduce(lambda x, y: x and y, map(lambda x: type(x) == str, list(predicate.values()))))
 

def check_predicates(predicates: list[dict], silent: bool) -> bool:
    if not bool(predicates):
        logging.error(f"The field 'predicates' is empty")
        return False
        
    faulty_predicates = list(filter(lambda p: not is_valid_predicate(p), predicates))
    
    if len(faulty_predicates) > 0:
        if not silent:
            logging.error(f"predicates - There are {len(faulty_predicates)} invalid predicates out of {len(predicates)}.")
            for faulty_pred in faulty_predicates:
                name = faulty_pred.get('value', None)
                not_allowed_fields = set(faulty_pred.keys()) - {'value', 'expanded', 'description', 'colour'}
                if name is None:
                    logging.error(f"\tUNKNOWN predicate has no 'value' field (its name).")
                if len(not_allowed_fields) > 0:
                    logging.error(f"\t{name} predicate has fields that are not allowed: {not_allowed_fields}")
                if {'value', 'expanded', 'description'}.issubset(faulty_pred.keys()):
                    if type(faulty_pred['value']) != str:
                        logging.error(f"\t'value' field is not a string. Detected type: {type(faulty_pred['value'])}")
                    if type(faulty_pred['expanded']) != str:
                        logging.error(f"\t'expanded' field is not a string. Detected type: {type(faulty_pred['expanded'])}")
                    if type(faulty_pred.get('description', '')) != str:
                        logging.error(f"\t'description' field is not a string. Detected type: {type(faulty_pred['description'])}")                   
                    
        return False
        
    return True
    
    
def is_valid_entry(entry: dict) -> bool:    
    return set(entry.keys()).issubset({'value', 'expanded', 'description'}) and type(entry['value']) == str and type(entry['expanded']) == str
    
    
def is_valid_value(value: dict, silent: bool) -> bool:

    if set(value.keys()) != {'predicate', 'entry'} or type(value['predicate']) != str or type(value['entry']) != list:      
        return False      
    
    faulty_entries = list(filter(lambda p: not is_valid_entry(p), value['entry']))
    
    if len(faulty_entries) > 0:
        if not silent:
            logging.error(f"values - There are invalid value entries.")
            for faulty_val in faulty_entries:

                name = faulty_val.get('value', None)
                not_allowed_fields = set(faulty_val.keys()) - {'value', 'expanded', 'description'}

                if name is None:
                    logging.error(f"\tUNKNOWN value has no 'value' field (its name).")

                if len(not_allowed_fields) > 0:
                    logging.error(f"\t{name} predicate has fields that are not allowed: {not_allowed_fields}")
                    
                if {'value', 'expanded'}.issubset(faulty_val.keys()):
                    if type(faulty_val['value']) != str:
                        logging.error(f"\t'value' field is not a string. Detected type: {(faulty_val['value'])}")
                    if type(faulty_val['expanded']) != str:
                        logging.error(f"\t'expanded' field is not a string. Detected type: {(faulty_val['expanded'])}")
                    if type(faulty_val.get('description', '')) != str:
                        logging.error(f"\t'description' field is not a string. Detected type: {(faulty_val['description'])}")
                    
        return False
        
    return True
    

def check_values(values: list[dict], silent: bool) -> bool:  
    if not bool(values): 
        if not silent:
            logging.warning(f"A taxonomy with no values is allowed: if it's not intended, please check.")
        return True
        
    faulty_values = list(filter(lambda p: not is_valid_value(p, silent), values))
    
    if len(faulty_values) > 0:
        if not silent:
            logging.error(f"values - There are invalid values.")

            for faulty_val in faulty_values:
                name = faulty_val.get('value', None)
                not_allowed_fields = set(faulty_val.keys()) - {'predicate', 'entry'}

                if len(not_allowed_fields) > 0:
                    logging.error(f"\t{name} predicate has fields that are not allowed: {not_allowed_fields}")

                if {'predicate', 'entry'}.issubset(faulty_val.keys()):
                    if type(faulty_val['predicate']) == str:
                        logging.error(f"\t'predicate' field is not a string")
                    if type(faulty_val['entry']) == list:
                        logging.error(f"\t'entry' field is not a list")
                    
        return False
        
    return True
    
    
def check_matches(file: dict, silent: bool) -> bool:
    matches = FreezableDict()
    result = True
    
    predicates = file.get('predicates')
    values = file.get('values', {})
    
    for pred in predicates:
        matches[pred['value']] = []
        
    matches.freeze()
    
    for val in values:
        for v in val['entry']:
            try:
                matches[val['predicate']] = v['value']
            except:
                result = False
                if not silent:
                    logging.error(f"The value {v['value']} has no valid matching predicate, as {val['predicate']} was not defined.")
    
    return result    


def check_configuration_file(file: dict, silent: bool) -> bool:
    """
    Performs the integrity check on the input machinetag.json file.
    Prints what's wrong with the file, is silent is False, otherwise just checks if the file is a valid MISP taxonomy file and returns a boolean.
    """
    if not bool(file):
        if not silent:
            logging.error("File is empty, check for trailing commas.")
        return False

    return check_fields(file.keys(), silent) and check_predicates(file.get('predicates', {}), silent) and check_values(file.get('values', {}), silent) and check_matches(file, silent)
    

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='A simple checker for MISP taxonomies files (machinetag.json).')

    # Add arguments
    parser.add_argument('file', help='Path to the input file.')
    parser.add_argument('-s', '--silent', action='store_true', default=False, help="Don't provide tips on how to fix the machinetag.json file.")

    # Parse arguments
    args = parser.parse_args()

    # Load JSON file
    data = load_json_file(args.file, args.silent)

    result = check_configuration_file(data, args.silent)
    
    if not args.silent:
        print(f"The input file is {'NOT ' if not result else ''}a valid configuration file")
        
    sys.exit(int(result))
    

if __name__ == "__main__":
    main()



import requests
import json
import time
import threading
import logging
import os
import sys

from datetime import datetime, timedelta

from airtable import Airtable

# Set up logging to file
logging.basicConfig(filename='recipe_logs.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Set up logging to screen
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)


class Automation:
    TRIGGERS = {
        "airtable_record_updated": {
            "description": "Triggered when a record is created or updated in Airtable",
        },
        "find_record": {
            "description": "Find a record based on specified text in a field",
        },
    }

    ACTIONS = {
        "send_webhook": {
            "description": "Sends a webhook to a specified URL",
        },
    }

    def __init__(self, trigger=None, actions=None, base_key=None, table_name=None, api_key=None, field_name=None, text_to_find=None, name=None, filters=[]):
        self.name = name
        self.last_execution_time = None

        self.processed_records = {}

        self.trigger = trigger
        
        self.actions = actions or [{"type": None, "filters": [], "output_name": None, "input_from": []}]
        
        self.base_key = base_key

        self.table_name = table_name
        self.api_key = api_key

        self.field_name = field_name
        self.text_to_find = text_to_find

        self.filters = filters


    def send_webhook(self, data, action):
        response = requests.post(action["webhook_url"], json=data)
        logging.info(f"{self.name}: Webhook sent to {action['webhook_url']} with data: {data}")
        return response.json()

    def matches_field(self, record):
        """
        Return true if the record does have a field and text is matched.
        """
        field_value = str(record['fields'].get(self.field_name, ""))
        matches_text = self.text_to_find in field_value

        if matches_text:
            logging.info(f"{self.name}: Detected record {record['id']} with text '{self.text_to_find}' in field '{self.field_name}'")
        return matches_text


def fetch_records(base_key, table_name, api_key):
    airtable = Airtable(base_key, table_name, api_key=api_key)
    logging.info("Fetching records from Airtable...")
    records = airtable.get_all()
    logging.info(f"Fetched {len(records)} records from Airtable")
    return records


def save_recipe(recipe, filename):
    with open(filename, 'w') as file:
        json.dump(vars(recipe), file, indent=4)
    logging.info(f"Recipe saved to {filename}")


def load_recipe(filename):
    with open(filename, 'r') as file:
        recipe_data = json.load(file)
        recipe_data.pop("last_execution_time", None)
        recipe_data.pop("processed_records", None)
        return Automation(**recipe_data)


def create_recipe():
    print("Creating a new recipe...")
    
    name = input("Step 1: Enter a name for this recipe: ")

    print(f"\n{name} - Step 2: Choose a Trigger")
    print("----------------------------------")
    trigger = select_option(Automation.TRIGGERS)

    print(f"\n{name} - Step 3: Choose an Action")
    print("----------------------------------")
    actions = []
    while True:
        action_dict = {}
        action_type = select_option(Automation.ACTIONS)
        action_dict["type"] = action_type
        
        if action_type == "send_webhook":
            webhook_url = input("\nEnter the webhook URL: ")
            action_dict["webhook_url"] = webhook_url
        
        action_filters = []
        add_filter = input(f"Do you want to add a filter for action {action_type}? (yes/no): ").strip().lower()
        while add_filter == "yes":
            field_name_to_filter = input("Enter the field name to apply the filter on: ")
            operator = input("Enter the operator (equals/contains/greater_than): ").strip().lower()
            value = input("Enter the value for the filter: ")
            action_filters.append({
                "field_name": field_name_to_filter,
                "operator": operator,
                "value": value
            })
            add_filter = input(f"Do you want to add another filter for action {action_type}? (yes/no): ").strip().lower()

        action_dict["filters"] = action_filters
        actions.append(action_dict)
        
        add_more = input("Do you want to add another action? (yes/no): ").strip().lower()
        if add_more != 'yes':
            break

    for action_dict in actions:
        # Add output name for action
        output_name = input(f"Enter an output name for action {action_dict['type']} (press enter to skip): ").strip()
        if output_name:
            action_dict["output_name"] = output_name

        # Add input from previous actions
        if actions.index(action_dict) != 0:  # skip for the first action
            input_from_str = input(f"Do you want to use outputs from previous actions as input for action {action_dict['type']}? If yes, specify comma-separated output names (e.g. output1,output2), otherwise press enter to skip: ").strip()
            if input_from_str:
                action_dict["input_from"] = [name.strip() for name in input_from_str.split(",")]

    base_key = input(f"{name} - Step 4: Enter the Airtable base key: ")
    table_name = input(f"{name} - Step 5: Enter the Airtable table name(KEY): ")
    api_key = input(f"{name} - Step 6: Enter the Airtable API key: ")

    field_name = None
    text_to_find = None
    if trigger == "find_record":
        field_name = input(f"{name} - Step 7: Enter the field name to search in: ")
        text_to_find = input(f"{name} - Step 8: Enter the text to find in the field: ")

    filters = []
    add_filter = input(f"{name} - Step 9: Do you want to add a filter? (yes/no): ").strip().lower()

    while add_filter == "yes":
        field_name_to_filter = input("Enter the field name to apply the filter on: ")
        
        operator = input("Enter the operator (equals/contains/greater_than): ").strip().lower()
        
        value = input("Enter the value for the filter: ")
        
        filters.append({
            "field_name": field_name_to_filter,
            "operator": operator,
            "value": value
        })

        # This prompt should be here, at the end of the loop, to ask again if user wants to add another filter.
        add_filter = input("Do you want to add another filter? (yes/no): ").strip().lower()
    
    return Automation(trigger, actions, base_key, table_name, api_key, field_name, text_to_find, name, filters)


def select_option(options):
    numbered_options = list(enumerate(options.items(), start=1))
    for number, (key, value) in numbered_options:
        print(f"{number}: {value['description']}")

    selected_option_key = None
    while selected_option_key is None:
        try:
            selection = int(input("Choose an option by entering the corresponding number: "))
            if 1 <= selection <= len(numbered_options):
                selected_option_key = numbered_options[selection - 1][1][0]
            else:
                print("Invalid choice. Please choose a valid option.")
        except ValueError:
            print("Please enter a valid number.")

    return selected_option_key

def matches_filters(record, filters):
    # If filters is None or an empty list, return True to allow all records
    if not filters:
        return True
    
    for filter_cond in filters:
        field_value = record['fields'].get(filter_cond["field_name"], "")
        if filter_cond["operator"] == "equals" and field_value and field_value != filter_cond["value"]:
            return False
        elif filter_cond["operator"] == "contains" and field_value and filter_cond["value"] not in field_value:
            return False
        elif filter_cond["operator"] == "greater_than" and field_value and float(field_value) <= float(filter_cond["value"]):
            return False
        # Add more operators as needed
    return True

def execute_recipe(recipe):
    recipe.is_running = True
    logging.info(f"Monitoring Airtable for changes for recipe {recipe.name} ...")
    airtable = Airtable(recipe.base_key, recipe.table_name, api_key=recipe.api_key)

    recipe.processed_records = {
        rec['id']: datetime.utcnow()
        for rec in airtable.get_all()
    }

    outputs = {}

    while True:
        records = airtable.get_all()
        recipe.last_execution_time = datetime.utcnow()

        for record in records:
            record_id = record['id']
            rec_last_modified = datetime.strptime(record['fields'].get('Last Modified', '1970-01-01T00:00:00.000Z'), "%Y-%m-%dT%H:%M:%S.%fZ")

            is_too_fresh = (datetime.utcnow() - rec_last_modified) < timedelta(seconds=10)
            is_new = record_id not in recipe.processed_records
            is_updated = not is_new and (recipe.processed_records[record_id] < rec_last_modified)

            if is_too_fresh:
                continue

            # ALL records
            pass

            # NEW records
            if is_new:
                logging.debug(f"{recipe.name}: New record {record_id}: {record}")
                if recipe.trigger == "find_record":
                    if recipe.matches_field(record):
                        for action in recipe.actions:
                            if action["type"] == "send_webhook":
                                if matches_filters(record, recipe.filters):
                                    if matches_filters(record, action.get('filters', [])):
                                        inputs = {}
                                        for input_name in action.get("input_from", []):
                                            inputs[input_name] = outputs.get(input_name, None)
                                        action_data = {}
                                        if "input_from" in action:
                                            action_data = {input_name: inputs[input_name] for input_name in action["input_from"]}
                                        else:
                                            action_data = {"record": record}
                                        result = recipe.send_webhook(data=action_data, action=action)
                                        if "output_name" in action:
                                            outputs[action["output_name"]] = result
                                        # recipe.send_webhook(data={"record": record}, action=action)
                                        recipe.processed_records[record_id] = recipe.last_execution_time

            # EXISTING but UPDATED records
            if is_updated and not is_new:
                logging.debug(f"{recipe.name}: Updated old record {record_id}: {record}")

            # NEW or UPDATEd records
            if is_updated or is_new:
                logging.debug(f"New or Updated record {record_id}: {record}")

                if recipe.trigger == "airtable_record_updated":
                    for action in recipe.actions:
                        if action["type"] == "send_webhook":
                            if matches_filters(record, recipe.filters):
                                if matches_filters(record, action.get('filters', [])):
                                    inputs = {}
                                    for input_name in action.get("input_from", []):
                                        inputs[input_name] = outputs.get(input_name, None)
                                    action_data = {}
                                    if "input_from" in action:
                                        action_data = {input_name: inputs[input_name] for input_name in action["input_from"]}
                                    else:
                                        action_data = {"record": record}
                                    result = recipe.send_webhook(data=action_data, action=action)
                                    if "output_name" in action:
                                        outputs[action["output_name"]] = result
                                    # recipe.send_webhook(data={"record": record}, action=action)
                                    recipe.processed_records[record_id] = recipe.last_execution_time

        if not recipe.is_running:
            break
        time.sleep(10)

    recipe.is_running = False


class RecipeManager:
    def __init__(self):
        self.recipes = []
        self.threads = []
        self.load_all_recipes()

    def add_recipe(self, recipe):
        recipe.is_running = False  # Set is_running to False by default
        recipe.is_thread_running = False  # Set is_thread_running to False by default
        self.recipes.append(recipe)
        thread = threading.Thread(target=execute_recipe, args=(recipe,))
        self.threads.append(thread)

    def start_all(self):
        if all(recipe.is_running for recipe in self.recipes):
            logging.info("All recipes are already running")
        else:
            for thread, recipe in zip(self.threads, self.recipes):
                if recipe.is_running:
                    # webhook_url = next((action['webhook_url'] for action in recipe.actions if action.get('webhook_url')), "Unknown")
                    logging.info(f"{recipe.name}: Recipe {recipe.name} is already running")
                else:
                    thread.start()
                    recipe.is_running = True
                    recipe.is_thread_running = True  # Mark the thread as running
                    # webhook_url = next((action['webhook_url'] for action in recipe.actions if action.get('webhook_url')), "Unknown")
                    logging.info(f"{recipe.name}: Recipe {recipe.name} started")

    def log_status(self):
        for recipe in self.recipes:
            status = "running" if recipe.is_thread_running else "stopped"  # Use is_thread_running instead of is_running
            logging.info(f"Recipe {recipe.name}: {recipe.webhook_url} is {status}")

    def load_all_recipes(self):
        for filename in os.listdir():
            if filename.endswith('.json'):
                recipe = load_recipe(filename)
                self.add_recipe(recipe)
        logging.info(f"Loaded {len(self.recipes)} recipes")

    def load_recipe_by_name(self, filename):
        if filename.endswith('.json') and os.path.exists(filename):
            recipe = load_recipe(filename)
            self.add_recipe(recipe)
            logging.info(f"Loaded recipe from {filename}")
            return recipe  # Return the loaded recipe
        else:
            logging.error(f"Recipe file {filename} not found.")
            return None
        
    def print_logs(self):
        with open('recipe_logs.log', 'r') as file:
            logs = file.read()
            print(logs)


def main_menu():
    print("Available commands:")
    print("  create - Create a new recipe")
    print("  start  - Start all recipes")
    print("  load   - Load a specific recipe by name (provide the recipe filename without '.json')")
    print("  status - View status of all recipes")
    print("  logs   - View the logs")
    print("  exit   - Exit the application")


def main():
    manager = RecipeManager()
    main_menu()
    while True:
        action = input("Enter a command: ")
        if action == 'create':
            user_recipe = create_recipe()
            filename = user_recipe.name + ".json"
            save_recipe(user_recipe, filename)
            logging.info(f"Recipe saved as {filename}")
            manager.add_recipe(user_recipe)
            print(f"Recipe '{user_recipe.name}' created.")
        elif action == 'start':
            manager.start_all()
            logging.info("All recipes started")
        elif action == 'load':
            recipe_name = input("Enter the name of the recipe (without '.json'): ")
            filename = recipe_name + ".json"
            loaded_recipe = manager.load_recipe_by_name(filename)
            if loaded_recipe:
                thread = threading.Thread(target=execute_recipe, args=(loaded_recipe,))
                thread.start()
                loaded_recipe.is_running = True
                loaded_recipe.is_thread_running = True
                logging.info(f"{loaded_recipe.name}: Recipe {loaded_recipe.webhook_url} started")
        elif action == 'status':
            manager.log_status()
        elif action == 'logs':
            manager.print_logs()
        elif action == 'exit':
            sys.exit(0)
        else:
            print("Unknown command. Please try again.")
            main_menu()


if __name__ == "__main__":
    main()
